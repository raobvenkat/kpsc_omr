import torch

# Returns True if a CUDA-compatible GPU is detected
print(torch.cuda.is_available())

# Optional: Get your GPU details
if torch.cuda.is_available():
    print(f"GPU Device Name: {torch.cuda.get_device_name(0)}")
    print(f"Total Devices Available: {torch.cuda.get_device_count()}")