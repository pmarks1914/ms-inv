import torch
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler

model_id = "stabilityai/stable-diffusion-2"
scheduler = EulerDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")

# Load model and move to MPS (Metal Performance Shaders) for Mac M1/M2
pipe = StableDiffusionPipeline.from_pretrained(model_id, scheduler=scheduler, torch_dtype=torch.float16)

# Use MPS if available, otherwise fallback to CPU
device = "mps" if torch.backends.mps.is_available() else "cpu"
pipe = pipe.to(device)

prompt = "Create a logo with the letter 'V'. Use a vibrant blue color for the 'V'. Use white background. Apply one vertical stroke with color white accross the bottom of the 'V'. Just one design. Ensure the design is professional."
image = pipe(prompt).images[0]

image.save("logo_2.png")

# For PyTorch with CUDA 11.8 support
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
