import os
from templates import AERender, AEAsset


def get_image(fname: str):
    return os.path.join(os.getcwd(), "media", fname).replace("C:\\", "file:///").replace("\\", "/")



starting_five = AERender(
    "Starting Five",
    "/Users/daktronics/Desktop/Starting 5 L3rd/Live Read Animations Desktop (converted).aep",
    "Alt Starting Lineups",
    "/Apps/CasparCG/media/StartingFive.mov",
    [
        AEAsset("image", "Team Logo", "drexel.png", get_image),
        AEAsset("image", "Player 1 Picture", "drexel-wbb/1.png", get_image),
        AEAsset("image", "Player 2 Picture", "drexel-wbb/1.png", get_image),
        AEAsset("image", "Player 3 Picture", "drexel-wbb/1.png", get_image),
        AEAsset("image", "Player 4 Picture", "drexel-wbb/1.png", get_image),
        AEAsset("image", "Player 5 Picture", "drexel-wbb/1.png", get_image)
    ]
)