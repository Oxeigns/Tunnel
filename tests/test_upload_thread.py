import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, patch

import app
from config import Config


class UploadTests(unittest.TestCase):
    def test_forwarding_owns_a_loop_in_request_thread(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        def make_client(*args, **kwargs):
            asyncio.get_running_loop()
            self.assertTrue(kwargs['in_memory'])
            return client
        settings = replace(app.settings, bot_token='test', api_id=1,
                           api_hash='test', log_group_id='-100123')
        with patch.object(app, 'settings', settings), patch.object(app, 'Client', make_client):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(app.forward_document, '/tmp/test-file', 'caption').result()
        client.send_document.assert_awaited_once_with(
            chat_id=-100123, document='/tmp/test-file', caption='caption')
        client.__aexit__.assert_awaited_once()

    def test_missing_bot_token_is_rejected(self):
        self.assertFalse(Config.validate_runtime(replace(app.settings, bot_token=None)))
