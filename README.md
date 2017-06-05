# grasp-rectangle-labelling

A labelling tool tool for grasp rectangles.

## GUI

![GUI](https://raw.githubusercontent.com/ulaval-damas/grasp-rectangle-labelling/master/Resources/gui.png "GUI")

## Requirements

```bash
pip install -r requirements.txt
```

## Label your images

1. Create a folder in `Images/` containing your **.jpg** images. Eg.: `Images/folder1`.
2. `python main.py`
3. Enter your directory in "Image Dir:" entry and press the `Load` button. Eg.: write "folder1" (you don't need to write "Images/")
4. Start labelling! Click on the image, draw the first edge, click, draw the second edge then click. The labels appear on the right panel and are saved in your directory in `Labels/`. Eg.: `Labels/folder1/ORIGINAL_IMAGE_NAME.txt`

## Help

Navigate between images using either the `Prev`, `Next` or `Go` button, or using keyboard keys `a` (previous) or `d` (next). Labels are always saved before changing images.

Delete a rectangle by first clicking on it in the right panel, then press either the `Delete` button or the `x` key. Clicking on a rectangle highlights it, so it is easier to locate it.

Print the image with labels using either the `Print` button or the `p` key. Labeled images are saved in your directory in `Labels/`. Eg.: `Labels/folder1/ORIGINAL_IMAGE_NAME_labeled.jpg`

Cancel drawing a rectangle by pressing the `ESC` key.

You can place example images in your directory in `Examples/`. Eg.: `Examples/folder1/example1.jpg`. Three randomly selected images will be shown in the left panel. This is useful to guide the user.

## Acknowledgements

[BBox-Label-Tool](https://github.com/puzzledqs/BBox-Label-Tool)



