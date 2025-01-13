# ---------------------------------------------------------------------------- #
#  serverlessllm                                                               #
#  copyright (c) serverlessllm team 2024                                       #
#                                                                              #
#  licensed under the apache license, version 2.0 (the "license");             #
#  you may not use this file except in compliance with the license.            #
#                                                                              #
#  you may obtain a copy of the license at                                     #
#                                                                              #
#                  http://www.apache.org/licenses/license-2.0                  #
#                                                                              #
#  unless required by applicable law or agreed to in writing, software         #
#  distributed under the license is distributed on an "as is" basis,           #
#  without warranties or conditions of any kind, either express or implied.    #
#  see the license for the specific language governing permissions and         #
#  limitations under the license.                                              #
# ---------------------------------------------------------------------------- #
import concurrent.futures
import os
from argparse import Namespace, _SubParsersAction

import requests

from sllm.cli._cli_utils import read_config
from sllm.serve.logger import init_logger

logger = init_logger(__name__)


class FineTuningCommand:
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        fine_tuning_parser = parser.add_parser(
            "fine-tuning", help="Fine-tuning base model."
        )
        fine_tuning_parser.add_argument(
            "--base_model", type=str, help="base_model name"
        )
        fine_tuning_parser.add_argument(
            "--config",
            type=str,
            help="fine-tuning configuration",
            default=os.path.join(
                os.path.dirname(__file__), "default_ft_config.json"
            ),
        )
        fine_tuning_parser.set_defaults(func=FineTuningCommand)

    def __init__(self, args: Namespace) -> None:
        self.base_model = args.base_model
        self.config = args.config
        self.url = (
            os.getenv("LLM_SERVER_URL", "http://127.0.0.1:8343/")
            + "fine-tuning"
        )

    def run(self) -> None:
        config = read_config(self.config)
        logger.info(f"Start fine-tuning base model {self.base_model}")
        result = self.fine_tuning(config)
        logger.info(f"{result}")

    def fine_tuning(self, config: dict) -> dict:
        headers = {"Content-Type": "application/json"}

        # Send POST request to the /fine-tuning endpoint
        response = requests.post(self.url, headers=headers, json=config)

        if response.status_code == 200:
            logger.info(f"{self.base_model} fine-tuned successful.")
            return response.json()
        else:
            logger.error(
                f"Failed to do fine-tuning. Status code: {response.status_code}"
            )
            logger.error(f"Response: {response.text}")
            return None