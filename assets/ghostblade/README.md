# 鬼刀系列高清壁纸资源目录

把图片放到这个目录，游戏会自动加载替换矢量绘制的背景。
没有图片时会自动回退到代码生成的矢量立绘，所以可以一张一张慢慢加。

## 文件名约定（固定）

| 槽位 | 文件名 | 关联存档 |
|---|---|---|
| 樱 | `sakura.jpg` | animeSakura |
| 星 | `star.jpg` | animeStar |
| 月 | `moon.jpg` | animeMoon |
| 雪 | `snow.jpg` | animeSnow |
| 焰 | `flame.jpg` | animeFlame |
| 海 | `ocean.jpg` | animeOcean |
| 霓 | `neon.jpg` | animeNeon |
| 暮 | `dusk.jpg` | animeDusk |
| 幻 | `rainbow.jpg` | animeRainbow |
| 神 | `goddess.jpg` | animeGoddess |

支持 `.jpg / .png / .webp`，但默认查找 `.jpg`。要用其它后缀，改 `raiden.html` 里
`GHOSTBLADE_FILES` 表的对应文件名即可。

## 推荐图片规格

- 比例：竖版（接近 480 × 700 / 2:3 / 9:16）
- 分辨率：≥ 720 × 1080，建议 1080 × 1620 / 1440 × 2160
- 体积：单张 ≤ 600KB（jpg q=85）以避免首帧加载抖动
- 内容：人物居中或下偏中（HUD 在顶部 36px，HP 条在底部 60px）

## 使用远程 URL（CDN / OSS / 图床）

如果不想把图打进仓库，可以在 `raiden.html` 顶部找到 `GHOSTBLADE_URLS`，填入你的图床地址：

```js
const GHOSTBLADE_URLS = {
  animeSakura: 'https://cdn.example.com/ghostblade/sakura.jpg',
  ...
};
```

URL 优先于本地文件。注意：

- 图床要支持 CORS（`Access-Control-Allow-Origin: *`），否则会被浏览器拒绝
- 防盗链开启的站点（如 ArtStation/Patreon）大概率会失败 → 自己 CDN/OSS 最稳

## ⚠️ 法律提示

「鬼刀 / SoulTaker」由 **WLOP（王凌枫）** 创作，**全系列受版权保护**。

- 公开互联网上的高清原图基本都是粉丝转载，**未获作者授权请勿用于公开发行**
- 自用 / 私服可用 Patreon 订阅原图、自购的官方画集扫描
- 公共发布请用 **公共许可（CC0、CC-BY 等）** 的同风格替代素材

仓库默认不附带任何图片，避免侵权。
