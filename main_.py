import os
import sys

import cv2
import time
import yaml
import vispy
import torch
import imageio
import numpy as np

from bilateral_filtering import sparse_bilateral_filtering
from mesh import read_ply, output_3d_photo_, write_ply
from networks import Inpaint_Color_Net, Inpaint_Depth_Net, Inpaint_Edge_Net
from utils import get_MiDaS_samples_, read_MiDaS_depth
from MiDaS import MiDaS_utils
from MiDaS.run import run_depth
from MiDaS.monodepth_net import MonoDepthNet


def config_adjust(sample, config):
    print(f"Running depth extraction at {time.time()}")
    if config['require_midas'] is True:
        run_depth([sample['ref_img_fi']], config['src_folder'], config['depth_folder'],
                  config['MiDaS_model_ckpt'], MonoDepthNet, MiDaS_utils, target_w=640)
    if 'npy' in config['depth_format']:
        config['output_h'], config['output_w'] = np.load(sample['depth_fi']).shape[:2]
    else:
        config['output_h'], config['output_w'] = imageio.imread(sample['depth_fi']).shape[:2]
    frac = config['longer_side_len'] / max(config['output_h'], config['output_w'])
    config['output_h'], config['output_w'] = int(config['output_h'] * frac), int(config['output_w'] * frac)
    config['original_h'], config['original_w'] = config['output_h'], config['output_w']
    return config


def gen_ply(sample, config):
    image = imageio.imread(sample['ref_img_fi'])

    # process gray image
    if image.ndim == 2:
        image = image[..., None].repeat(3, -1)
    if np.sum(np.abs(image[..., 0] - image[..., 1])) == 0 and np.sum(np.abs(image[..., 1] - image[..., 2])) == 0:
        config['gray_image'] = True
    else:
        config['gray_image'] = False

    # resize image to config
    image = cv2.resize(image, (config['output_w'], config['output_h']), interpolation=cv2.INTER_AREA)

    # process to output ply file
    depth = read_MiDaS_depth(sample['depth_fi'], 3.0, config['output_h'], config['output_w'])
    vis_photos, vis_depths = sparse_bilateral_filtering(depth.copy(), image.copy(), config,
                                                        num_iter=config['sparse_iter'], spdb=False)
    depth = vis_depths[-1]
    model = None

    if isinstance(config["gpu_ids"], int) and (config["gpu_ids"] >= 0):
        device = config["gpu_ids"]
    else:
        device = "cpu"

    print(f"running on device {device}")

    torch.cuda.empty_cache()
    print("Start Running 3D_Photo ...")

    print(f"Loading edge model at {time.time()}")
    depth_edge_model = Inpaint_Edge_Net(init_weights=True)
    depth_edge_weight = torch.load(config['depth_edge_model_ckpt'],
                                   map_location=torch.device(device))
    depth_edge_model.load_state_dict(depth_edge_weight)
    depth_edge_model = depth_edge_model.to(device)
    depth_edge_model.eval()

    print(f"Loading depth model at {time.time()}")
    depth_feat_model = Inpaint_Depth_Net()
    depth_feat_weight = torch.load(config['depth_feat_model_ckpt'],
                                   map_location=torch.device(device))
    depth_feat_model.load_state_dict(depth_feat_weight, strict=True)
    depth_feat_model = depth_feat_model.to(device)
    depth_feat_model.eval()
    depth_feat_model = depth_feat_model.to(device)

    print(f"Loading rgb model at {time.time()}")
    rgb_model = Inpaint_Color_Net()
    rgb_feat_weight = torch.load(config['rgb_feat_model_ckpt'],
                                 map_location=torch.device(device))
    rgb_model.load_state_dict(rgb_feat_weight)
    rgb_model.eval()
    rgb_model = rgb_model.to(device)

    # print(f"Writing depth ply (and basically doing everything) at {time.time()}")
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} Writing depth ply (and basically doing everything) at ')
    mesh_fi = os.path.join(config['mesh_folder'], sample['src_pair_name'] + '.ply')
    ply_data = write_ply(image,
                         depth,
                         sample['int_mtx'],
                         mesh_fi,
                         config,
                         rgb_model,
                         depth_edge_model,
                         depth_edge_model,
                         depth_feat_model)

    torch.cuda.empty_cache()


def video3d(sample, config, id_type):
    image = imageio.imread(sample['ref_img_fi'])

    # process gray image
    if image.ndim == 2:
        image = image[..., None].repeat(3, -1)
    if np.sum(np.abs(image[..., 0] - image[..., 1])) == 0 and np.sum(np.abs(image[..., 1] - image[..., 2])) == 0:
        config['gray_image'] = True
    else:
        config['gray_image'] = False

    # resize image to config
    image = cv2.resize(image, (config['output_w'], config['output_h']), interpolation=cv2.INTER_AREA)

    # Load ply data files
    ply_data = read_ply(os.path.join(config['mesh_folder'], sample['src_pair_name'] + '.ply'))

    output_3d_photo_(image, sample, ply_data, config, id_type)


if __name__ == '__main__':
    uuid = (sys.argv[1:] + [''])[0]
    type_id = (sys.argv[2:] + [None])[0]

    config = yaml.load(open('argument.yml', 'r'))

    if config['offscreen_rendering'] is True:
        vispy.use(app='egl')

    sample = get_MiDaS_samples_(uuid, config)

    # process some config
    config = config_adjust(sample, config)
    if type_id is not None:
        video_file = config['video_folder'] + '/' + uuid + '_' + config['video_postfix'][int(type_id)] + '.mp4'
        video_file_in_process = video_file + '.in_process'
        open(video_file_in_process, mode='a').close()  # create empty file

        video3d(sample=get_MiDaS_samples_(uuid, config), config=config, id_type=int(type_id))
    else:
        gen_ply(sample=sample, config=config)
