"""真实下单适配器 —— **未完成，因为拿不到 ABI**。

这个会话的出网被组织级 egress 策略全封（tapeout.net / BSC RPC / bscscan 全部
403 CONNECT），所以市场合约地址和 ABI 无法获取。简报 §7 也把这些列为未确认项。

**唯一缺的就是这个文件。** 其余模块（估值、报价、风控、回测）都不依赖 ABI，
已经可跑可测。补齐需要下面这些信息，拿到后实现 5 个方法即可接上：

必需
  1. 市场合约地址（简报只给了 PodLens 只读合约 0xdD20...30d8，那是查询用的）
  2. 合约 ABI（或已验证源码）
  3. 晶体管的代币模型：ERC-1155 的 tokenId？ERC-20？还是合约内部记账？
  4. 撮合模型：链上订单簿 / 荷兰拍 / AMM / 链下签名订单？—— 这决定 place 的语义
  5. 挂单是否需要先 approve，以及 approve 给谁
  6. 手续费：taker/maker 各多少 bps，谁付

强烈建议先确认
  7. 撤单是否退还全部本金（决定改单的真实成本）
  8. 单账户最大挂单数
  9. 是否有链上滑点保护参数

接好之后务必先用 BSC 测试网或极小额跑通，再把 BotConfig.dry_run 关掉。
"""
from __future__ import annotations

from venue import BookTop, Fill, Order, Quote, Venue


class MissingABIError(NotImplementedError):
    pass


_MSG = ("链上适配器未实现：缺少市场合约地址与 ABI。"
        "见 chain.py 模块文档列出的 9 项信息。")


class ChainVenue(Venue):
    """占位实现。骨架保留，方法体全部抛异常，避免被误当成能用的东西。"""

    def __init__(self, rpc_url: str, market_address: str, abi: list | None = None,
                 account: str | None = None, private_key: str | None = None):
        self.rpc_url = rpc_url
        self.market_address = market_address
        self.abi = abi
        self.account = account
        self._pk = private_key          # 不要 log 这个
        if not abi:
            raise MissingABIError(_MSG)

    def top(self, leg: str) -> BookTop:
        raise MissingABIError(_MSG)

    def open_orders(self, leg: str) -> list[Order]:
        raise MissingABIError(_MSG)

    def place(self, leg: str, quote: Quote) -> Order:
        raise MissingABIError(_MSG)

    def cancel(self, order: Order) -> None:
        raise MissingABIError(_MSG)

    def drain_fills(self) -> list[Fill]:
        raise MissingABIError(_MSG)
