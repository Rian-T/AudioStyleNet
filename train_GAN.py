import argparse
import importlib
import os
import torch
import wandb

from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from torchsummaryX import summary

import dataloader

from models.gan_models import weights_init
from solver import GANSolver

HOME = os.path.expanduser('~')
PLOT_GRADS = False
LOG_RUN = True

if PLOT_GRADS:
    print("WARNING: Plot gradients is on. This may cause slow training time!")


""" Load config """

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config',
                    type=str,
                    default='ravdess_im_gan',
                    help='name of config')
args = parser.parse_args()

config = importlib.import_module('configs.' + args.config).config


""" Init wandb """

if LOG_RUN:
    writer = SummaryWriter()
    wandb.init(project="emotion-pix2pix", config=config, sync_tensorboard=True)
else:
    writer = None


""" Add a seed to have reproducible results """

seed = 123
torch.manual_seed(seed)


""" Configure training with or without cuda """

if config.use_cuda and torch.cuda.is_available():
    device = torch.device("cuda")
    torch.cuda.manual_seed(seed)
    kwargs = {'pin_memory': True}
    print("GPU available. Training on {}.".format(device))
else:
    device = torch.device("cpu")
    torch.set_default_tensor_type('torch.FloatTensor')
    kwargs = {}
    print("No GPU. Training on CPU.")


ds = dataloader.RAVDESSDSPix2Pix(config.data_path,
                                 data_format=config.data_format,
                                 use_gray=config.use_gray,
                                 max_samples=None,
                                 sequence_length=config.sequence_length,
                                 step_size=config.step_size,
                                 image_size=config.image_size)

print("Found {} samples in total".format(len(ds)))

data_loader = DataLoader(ds,
                         batch_size=config.batch_size,
                         num_workers=8,
                         shuffle=True,
                         drop_last=True)


""" Show data example """

sample = next(iter(data_loader))
print('Input Shape: {}'.format(sample['A'].shape))
# ds.show_sample()


""" Initialize models, solver, optimizers and loss functions """

# Initialize models
generator = config.generator
generator.train()
generator.to(device)
generator.apply(weights_init)

discriminator = config.discriminator
discriminator.train()
discriminator.to(device)
discriminator.apply(weights_init)

# if LOG_RUN:
#     # wandb.watch(generator)
#     writer.add_graph(generator, sample['A'].to(device))
#     # writer.add_graph(discriminator, (sample['B'], sample['A']))

# Initialize Loss functions
criterion_gan = config.criterion_gan
criterion_pix = config.criterion_pix

# Initialize optimizers
optimizer_g = config.optimizer_g
optimizer_d = config.optimizer_d

# Initialize solver
solver = GANSolver(generator, discriminator, ds.mean, ds.std)


""" Do training """

solver.train_model(optimizer_g,
                   optimizer_d,
                   criterion_gan,
                   criterion_pix,
                   device,
                   data_loader,
                   config,
                   config.lambda_pixel,
                   PLOT_GRADS,
                   LOG_RUN,
                   writer)
