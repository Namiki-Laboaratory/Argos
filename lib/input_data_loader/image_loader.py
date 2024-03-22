import os
import glob

from lib.input_data_loader import BaseInputDataLoader


class ImageDataLoader(BaseInputDataLoader):
    def __init__(self, *args):
        super(ImageDataLoader, self).__init__(*args)
        self.files = []
        if type(self.data_path) == str:
            if os.path.isdir(self.data_path):
                image_format = ['.jpg', '.jpeg', '.png', '.tif', '.exr']
                self.files = sorted(glob.glob('%s/*.*' % self.data_path))
                self.files = list(filter(lambda x: os.path.splitext(x)[
                                                       1].lower() in image_format, self.files))
            elif os.path.isfile(self.data_path):
                self.files = [self.data_path]
            else:
                raise

        elif type(self.data_path) == list:
            self.files = self.data_path

        self.len = len(self.files)  # number of image files
        assert self.len > 0, 'No images found in ' + self.data_path

    def __next__(self):
        super(ImageDataLoader, self).__next__()
        if self.count == len(self):
            raise StopIteration
        return self.read_image(self.count)
