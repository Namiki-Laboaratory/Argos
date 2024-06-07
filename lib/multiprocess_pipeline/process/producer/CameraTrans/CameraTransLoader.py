import time
import inspect

from ..CameraTrans import CameraTransProcess_Master
from lib.multiprocess_pipeline.workers.camera_trans_loader import factory_camera_trans_loader, E_CameraTransLoaderName
from lib.multiprocess_pipeline.process.SharedDataName import E_PipelineSharedDataName


class CameraTransLoaderProcess(CameraTransProcess_Master):
    prefix = 'Argus-SubProcess-CameraTransLoader_'
    dir_name = 'camera_trans_input'
    log_name = 'Camera_Trans_Loader_Log'

    def __init__(self,
                 loader: str,
                 source,
                 *args,
                 load_buffer=8,
                 **kwargs,
                 ):

        if loader not in E_CameraTransLoaderName.__members__.keys():
            raise KeyError(f'loader {loader} is not a valid loader')
        self.loader = factory_camera_trans_loader[loader]

        loader_kwargs = {}
        tmp = inspect.signature(self.loader).bind(source, **kwargs)
        tmp.apply_defaults()
        tmp_keys = tmp.arguments.keys()
        for k in tmp_keys:
            if k in kwargs.keys():
                loader_kwargs[k] = kwargs.pop(k)

        super(CameraTransLoaderProcess, self).__init__(*args, **kwargs)

        self.source = source
        self.load_buffer = load_buffer
        self.loader_kwargs = loader_kwargs

        self.count = 0
        self.load_time = 0
        self.dps_avg = 0
        self.dps_cur = 0

    def run_begin(self) -> None:
        super(CameraTransLoaderProcess, self).run_begin()

        self.logger.info(f"Start Creating Camera Transform Loader @ "
                         f"{self.source if isinstance(self.source, str) else 'Fixed Camera'}")
        self.logger.info(f'Waiting read @ {self.source}')
        self.loader = self.loader(self.source, **self.loader_kwargs)

    def run_action(self) -> None:
        self.logger.info("Start loading camera transform")

        hub_camera_trans = \
            self.data_hub.dict_shared_data[self.pipeline_name][E_PipelineSharedDataName.CameraTransform.name]
        hub_camera_timestamp = \
            self.data_hub.dict_shared_data[self.pipeline_name][E_PipelineSharedDataName.TransformTimestamp.name]

        each_frame_start_time = time.perf_counter()
        start_time = time.perf_counter()
        for timestamp, path, trans in self.loader:
            if timestamp and trans:
                each_frame_end_time = time.perf_counter()
                delta_time_each = each_frame_end_time - each_frame_start_time
                delta_time_all = each_frame_end_time - start_time

                hub_camera_timestamp.set(timestamp)
                hub_camera_trans.set(trans)
                self.count += 1

                self.dps_avg = self.count / delta_time_all
                self.dps_cur = 1 / delta_time_each

                if self.count % 10 == 0 and self.count != 0:
                    self.logger.info(
                        f'Processing frame {self.count}: '
                        f'average dps: {self.dps_avg:.2f}, '
                        f'current dps: {self.dps_cur:.2f}; '
                    )

                each_frame_start_time = time.perf_counter()

        end_time = time.perf_counter()
        self.load_time = end_time - start_time

    def run_end(self) -> None:
        self.logger.info(
            f"Total receive {self.loader.count} frames in {self.load_time} s"
        )

        hub_camera_trans = \
            self.data_hub.dict_shared_data[self.pipeline_name][E_PipelineSharedDataName.CameraTransform.name]
        hub_camera_timestamp = \
            self.data_hub.dict_shared_data[self.pipeline_name][E_PipelineSharedDataName.TransformTimestamp.name]

        if not self.opt.realtime:
            while hub_camera_trans.size()[0] > 0:
                try:
                    hub_camera_trans.get()
                    hub_camera_timestamp.get()
                except RuntimeError:
                    pass

        super().run_end()
        self.logger.info('-' * 5 + 'Camera Transform Receiver Finished' + '-' * 5)
