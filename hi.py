import torch
import easyocr

# 1. Verify PyTorch sees the hardware
print(f"PyTorch CUDA Status: {torch.cuda.is_available()}")
print(f"Targeting Hardware: {torch.cuda.get_device_name(0)}")


#test123