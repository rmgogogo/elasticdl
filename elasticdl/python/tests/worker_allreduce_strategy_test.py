# Copyright 2020 The ElasticDL Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest

from elasticdl.proto import elasticdl_pb2
from elasticdl.python.common.args import parse_worker_args
from elasticdl.python.tests.test_utils import get_mnist_dataset
from elasticdl.python.worker.worker import Worker
from elasticdl_client.common.constants import DistributionStrategy


class WorkerAllReduceStrategyTest(unittest.TestCase):
    def setUp(self):
        self._model_zoo_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "../../../model_zoo"
        )
        self._model_def = "mnist.mnist_functional_api.custom_model"
        self._batch_size = 16
        self._test_steps = 10
        self._workers = []
        self._create_worker(2)

    def _create_worker(self, worker_num, max_allreduce_retry_num=0):
        for i in range(worker_num):
            arguments = [
                "--worker_id",
                i,
                "--num_workers",
                worker_num,
                "--job_type",
                elasticdl_pb2.TRAINING,
                "--minibatch_size",
                self._batch_size,
                "--model_zoo",
                self._model_zoo_path,
                "--model_def",
                self._model_def,
                "--distribution_strategy",
                DistributionStrategy.ALLREDUCE,
            ]
            args = parse_worker_args(arguments)
            worker = Worker(
                args, max_allreduce_retry_num=max_allreduce_retry_num
            )
            self._workers.append(worker)

    def test_collect_gradients_with_allreduce_success_case(self):
        worker = self._workers[0]
        train_db, _ = get_mnist_dataset(self._batch_size)
        for step, (x, y) in enumerate(train_db):
            if step == 0:
                worker._run_model_call_before_training(x)
            w_loss, w_grads = worker.training_process_eagerly(x, y)
            if step == self._test_steps:
                break
            self.assertEqual(
                worker._collect_gradients_with_allreduce_robust(w_grads), True,
            )

    def test_collect_gradients_with_allreduce_failure_case(self):
        worker = self._workers[1]
        train_db, _ = get_mnist_dataset(self._batch_size)
        for step, (x, y) in enumerate(train_db):
            if step == 0:
                worker._run_model_call_before_training(x)
            if step == self._test_steps:
                break
            self.assertEqual(
                worker._calculate_grads_and_report_with_allreduce(None),
                False,
                "Should fail when no data is received",
            )


if __name__ == "__main__":
    unittest.main()
