import asyncio

import httpx

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import ComponentType
from astrbot.api.star import Context, Star, register

PLUGIN_NAME = "astrbot_plugin_hof_watcher"


@register(PLUGIN_NAME, "AstrBot Community", "HallOfFame QQ 群消息采集插件", "1.0.0")
class HofWatcherPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.base_url = config.get("base_url", "http://localhost:9090")
        self.enabled_groups = config.get("enabled_groups", [])
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    async def initialize(self):
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))

    async def _ensure_client(self):
        """Lazy-init the HTTP client in case initialize() hasn't completed."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))

    # ---- Auto-collect: all group text messages ----
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        group_id = event.get_group_id()

        # Check if group is enabled
        if not self.enabled_groups or str(group_id) not in [
            str(g) for g in self.enabled_groups
        ]:
            return

        messages = event.get_messages()

        # Only collect messages where all components are Plain
        text_parts = []
        for comp in messages:
            if comp.type == ComponentType.Plain:
                text_parts.append(comp.text)
            else:
                return  # Non-text component found, skip

        content = "".join(text_parts).strip()
        if not content:
            return

        await self._upload_message(
            qqgroup=str(group_id),
            qqnumber=event.get_sender_id(),
            speaker=event.get_sender_name(),
            content=content,
        )
        # Silent — no reply on success

    # ---- Manual import command: /hall add ----
    @filter.command_group("hall")
    def hall(self):
        pass

    @filter.permission_type(filter.PermissionType.ADMIN)
    @hall.command("add")
    async def hall_add(self, event: AstrMessageEvent):
        messages = event.get_messages()

        # Find the Reply component (quoted message)
        reply = None
        for comp in messages:
            if comp.type == ComponentType.Reply:
                reply = comp
                break

        if not reply:
            yield event.plain_result("请引用一条消息再使用 /hall add 指令。")
            return

        if not reply.chain:
            yield event.plain_result("无法获取被引用的消息内容。")
            return

        # Extract text and images from the quoted message chain
        text_parts = []
        image_urls = []
        for comp in reply.chain:
            if comp.type == ComponentType.Plain:
                text_parts.append(comp.text)
            elif comp.type == ComponentType.Image:
                img_url = comp.url or comp.file or ""
                if img_url:
                    image_urls.append(img_url)
            # Ignore all other component types

        content = "".join(text_parts).strip()

        if not content and not image_urls:
            yield event.plain_result("被引用的消息没有可采集的内容。")
            return

        # Get sender info from the quoted message
        qqnumber = str(reply.sender_id) if reply.sender_id else ""
        speaker = reply.sender_nickname or ""

        if not qqnumber:
            yield event.plain_result("无法获取被引用消息的发送者信息。")
            return

        # Download image binaries
        await self._ensure_client()
        image_binaries = []
        for img_url in image_urls:
            try:
                resp = await self._client.get(img_url)
                if resp.status_code == 200:
                    image_binaries.append(resp.content)
                else:
                    logger.warning(
                        f"下载图片失败: HTTP {resp.status_code}, url={img_url}"
                    )
            except Exception as e:
                logger.error(f"下载图片异常: {e}, url={img_url}")

        success = await self._import_message(
            qqgroup=str(event.get_group_id()),
            qqnumber=qqnumber,
            speaker=speaker,
            content=content or "",
            files=image_binaries,
        )

        if success:
            yield event.plain_result("言论已成功导入！")
        else:
            yield event.plain_result("导入失败，请查看日志。")

    # ---- HTTP helpers ----

    async def _upload_message(
        self, qqgroup: str, qqnumber: str, speaker: str, content: str
    ) -> bool:
        """Upload to /api/bot/upload (multipart/form-data)."""
        await self._ensure_client()
        try:
            url = f"{self.base_url.rstrip('/')}/api/bot/upload"
            resp = await self._client.post(
                url,
                data={
                    "qqgroup": qqgroup,
                    "qqnumber": qqnumber,
                    "speaker": speaker,
                    "content": content,
                },
                files=[],
            )
            if resp.status_code != 200:
                logger.error(
                    f"[HofWatcher] 上传消息失败: HTTP {resp.status_code}, {resp.text}"
                )
                return False
            data = resp.json()
            if data.get("code") != 10200:
                logger.error(f"[HofWatcher] 上传消息失败: {data}")
                return False
            return True
        except httpx.HTTPError as e:
            logger.error(f"[HofWatcher] 上传消息网络异常: {e}")
            return False
        except Exception as e:
            logger.error(f"[HofWatcher] 上传消息未知异常: {e}")
            return False

    async def _import_message(
        self,
        qqgroup: str,
        qqnumber: str,
        speaker: str,
        content: str,
        files: list[bytes] | None = None,
    ) -> bool:
        """Upload to /api/bot/import (multipart/form-data)."""
        await self._ensure_client()
        try:
            url = f"{self.base_url.rstrip('/')}/api/bot/import"
            file_params = []
            if files:
                for i, file_data in enumerate(files):
                    file_params.append(
                        ("files", (f"image_{i}.jpg", file_data, "image/jpeg"))
                    )

            resp = await self._client.post(
                url,
                data={
                    "qqgroup": qqgroup,
                    "qqnumber": qqnumber,
                    "speaker": speaker,
                    "content": content,
                },
                files=file_params if file_params else None,
            )
            if resp.status_code != 200:
                logger.error(
                    f"[HofWatcher] 导入消息失败: HTTP {resp.status_code}, {resp.text}"
                )
                return False
            data = resp.json()
            if data.get("code") != 10200:
                logger.error(f"[HofWatcher] 导入消息失败: {data}")
                return False
            return True
        except httpx.HTTPError as e:
            logger.error(f"[HofWatcher] 导入消息网络异常: {e}")
            return False
        except Exception as e:
            logger.error(f"[HofWatcher] 导入消息未知异常: {e}")
            return False

    async def terminate(self):
        """Cleanup when plugin is unloaded."""
        if self._client:
            await self._client.aclose()
            self._client = None
