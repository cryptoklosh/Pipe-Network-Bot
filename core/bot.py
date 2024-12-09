import random
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict

import pytz
from Jam_Twitter_API.account_async import TwitterAccountAsync
from Jam_Twitter_API.errors import TwitterError, TwitterAccountSuspended
from loguru import logger
from loader import config
from models import Account, OperationResult
from utils import error_handler, url_to_params_dict

from .api import PipeNetworkAPI
from database import Accounts


class Bot(PipeNetworkAPI):
    def __init__(self, account: Account):
        super().__init__(account)
        self.account_data = account


    @error_handler(return_operation_result=True)
    async def process_registration(self) -> OperationResult:
        referral_code = random.choice(config.referral_codes)
        await self.register(referral_code=referral_code)

        logger.success(f"Account: {self.account_data.email} | Registration successful")
        return OperationResult(
            identifier=self.account_data.email,
            data=self.account_data.password,
            status=True
        )

    @error_handler(return_operation_result=False)
    async def process_farming_actions(self) -> None:
        if not await self._prepare_account():
            return

        node_data = await self.get_node_data()
        if not node_data:
            return

        await self._process_node(node_data)
        await self._update_sleep_time()
        await self._process_heartbeat()

        if config.show_points_stats:
            response = await self.points_in_extension()
            logger.info(f"Account: {self.account_data.email} | Total Points: {response['points']}")


    @error_handler(return_operation_result=True)
    async def process_bind_twitter(self):
        if not await self._prepare_account():
            return OperationResult(
                identifier=self.account_data.email,
                data=f"{self.account_data.password}:{self.account_data.twitter_token}",
                status=False
            )

        logger.info(f"Account: {self.account_data.email} | Binding Twitter...")
        twitter_bind_params = await self.get_twitter_bind_params()

        if twitter_bind_params.get("status", "") == "User already verified":
            logger.warning(f"Account: {self.account_data.email} | Twitter account already bound")
            if await self.process_twitter_status():
                return OperationResult(
                    identifier=self.account_data.email,
                    data=f"{self.account_data.password}:{self.account_data.twitter_token}",
                    status=True
                )
            else:
                return OperationResult(
                    identifier=self.account_data.email,
                    data=f"{self.account_data.password}:{self.account_data.twitter_token}",
                    status=False
                )

        elif not twitter_bind_params.get("url"):
            logger.error(f"Account: {self.account_data.email} | Failed to get twitter bind params: {twitter_bind_params}")
            return OperationResult(
                identifier=self.account_data.email,
                data=f"{self.account_data.password}:{self.account_data.twitter_token}",
                status=False
            )

        else:
            twitter_bind_params = url_to_params_dict(twitter_bind_params["url"])
            logger.info(f"Account: {self.account_data.email} | Twitter bind params received, binding account...")


        try:
            twitter_account = await TwitterAccountAsync.run(auth_token=self.account_data.twitter_token, proxy=self.account_data.proxy.as_url)
            approved_code = await twitter_account.bind_account_v2(twitter_bind_params)
            bound_data = await self.bind_twitter(twitter_bind_params["state"], approved_code)

            if isinstance(bound_data, dict) and bound_data.get("status", "") == "success":
                logger.success(f"Account: {self.account_data.email} | Twitter account bound")
                if await self.process_twitter_status():
                    return OperationResult(
                        identifier=self.account_data.email,
                        data=f"{self.account_data.password}:{self.account_data.twitter_token}",
                        status=True
                    )
                else:
                    return OperationResult(
                        identifier=self.account_data.email,
                        data=f"{self.account_data.password}:{self.account_data.twitter_token}",
                        status=False
                    )

            logger.error(f"Account: {self.account_data.email} | Failed to bind twitter: {bound_data}")

        except TwitterError as error:
            logger.error(f"Account: {self.account_data.email} | Failed to bind twitter (APIError): {error}")

        except TwitterAccountSuspended:
            logger.error(f"Account: {self.account_data.email} | Twitter account is suspended")

        return OperationResult(
            identifier=self.account_data.email,
            data=f"{self.account_data.password}:{self.account_data.twitter_token}",
            status=True
        )


    @error_handler(return_operation_result=False)
    async def process_twitter_status(self) -> bool:
        follow_status = await self.twitter_follow_status()
        if follow_status.get("status") == "User already verified":
            logger.success(f"Account: {self.account_data.email} | Twitter Username: {follow_status['user']['username']} | Reward: {follow_status['user']['reward']} points")
            return True

        logger.error(f"Account: {self.account_data.email} | Twitter follow status: {follow_status}")
        return False

    async def _prepare_account(self) -> bool:
        account = await Accounts.get_account(email=self.account_data.email)
        if not account:
            return await self.login_new_account()

        if await self.handle_sleep(account.sleep_until):
            return False

        self.session.headers = account.headers
        return True

    @error_handler(return_operation_result=False)
    async def _process_node(self, node_data: Dict[str, Any]) -> None:
        node_id = str(node_data["node_id"])
        node_ip = str(node_data["ip"])

        node_latency = await self.test_node_latency(node_ip)
        if node_latency is None:
            logger.error(f"Account: {self.account_data.email} | Failed to test node latency")
            return

        response = await self.test_ping(
            node_id=node_id,
            ip=node_ip,
            latency=str(node_latency)
        )

        logger.success(
            f"Account: {self.account_data.email} | "
            f"Node tested | Received points: {response['points']}"
        )


    @error_handler(return_operation_result=False)
    async def _process_heartbeat(self) -> None:
        account = await Accounts.get_account(email=self.account_data.email)
        if await self.handle_heartbeat(account.next_heartbeat_in):
            return

        logger.info(f"Account: {self.account_data.email} | Sending heartbeat...")
        geo_location = await self.get_geo_location()

        await self.heartbeat(ip=geo_location["ip"], location=geo_location["location"], timestamp=int(time.time() * 1000))
        await self._update_sleep_time(heartbeat=True)

        logger.success(f"Account: {self.account_data.email} | Heartbeat sent")

    async def _update_sleep_time(self, heartbeat: bool = False) -> None:
        if heartbeat:
            sleep_until = self.get_next_heartbeat_time()
            await Accounts.set_next_heartbeat_in(self.account_data.email, sleep_until)
            logger.debug(
                f"Account: {self.account_data.email} | "
                f"Next heartbeat time updated to {sleep_until}"
            )

        else:
            sleep_until = self.get_sleep_until()
            await Accounts.set_sleep_until(self.account_data.email, sleep_until)
            logger.debug(
                f"Account: {self.account_data.email} | "
                f"Sleep time updated to {sleep_until}"
            )

    @error_handler(return_operation_result=False)
    async def get_node_data(self) -> Optional[Dict[str, Any]]:
        response = await self.nodes()
        if not response or not response.text:
            return None

        node_data = response.json()
        if not node_data:
            return None

        node = node_data[0]
        if not self._validate_node_data(node):
            return None

        return node

    @staticmethod
    def _validate_node_data(node: Dict[str, Any]) -> bool:
        required_fields = {'node_id', 'ip'}
        return all(field in node for field in required_fields)

    @error_handler(return_operation_result=False)
    async def login_new_account(self) -> bool:
        logger.info(f"Account: {self.account_data.email} | Logging in via extension...")
        await self.login_in_extension()

        await Accounts.create_account(
            email=self.account_data.email,
            headers=self.session.headers
        )
        logger.success(f"Account: {self.account_data.email} | Logged in | Session saved")
        return True

    @staticmethod
    def get_sleep_until() -> datetime:
        duration = timedelta(seconds=config.keepalive_interval)
        return datetime.now(pytz.UTC) + duration

    @staticmethod
    def get_next_heartbeat_time() -> datetime:
        duration = timedelta(hours=config.heartbeat_interval)
        return datetime.now(pytz.UTC) + duration

    async def handle_sleep(self, sleep_until: datetime) -> bool:
        if not sleep_until:
            return False

        current_time = datetime.now(pytz.UTC)
        sleep_until = sleep_until.replace(tzinfo=pytz.UTC)

        if sleep_until > current_time:
            sleep_duration = (sleep_until - current_time).total_seconds()
            logger.debug(
                f"Account: {self.account_data.email} | "
                f"Next node testing in {sleep_until} "
                f"(duration: {sleep_duration:.2f} seconds)"
            )
            return True

        return False


    async def handle_heartbeat(self, next_heartbeat_in: datetime) -> bool:
        if not next_heartbeat_in:
            return False

        current_time = datetime.now(pytz.UTC)
        next_heartbeat_in = next_heartbeat_in.replace(tzinfo=pytz.UTC)

        if next_heartbeat_in > current_time:
            heartbeat_duration = (next_heartbeat_in - current_time).total_seconds() / 3600
            logger.debug(
                f"Account: {self.account_data.email} | "
                f"Next heartbeat in {next_heartbeat_in} "
                f"(duration: {heartbeat_duration:.2f} hours)"
            )
            return True

        return False
