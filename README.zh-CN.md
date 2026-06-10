# TextVision

[English](README.md)

TextVision 是一个本地插件，用来帮助纯文本模型或不支持图片输入的模型处理图片。它会把图片文件转换成结构化的文本证据包，让模型只基于 OCR 文本、文件信息和明确的局限性来回答。

它适合把 DeepSeek、本地大模型或其他纯文本 agent 用在截图、错误弹窗、SVG、图片文件等场景里，避免模型在看不到图片时编造视觉细节。

## 包含什么

- `textvision`：CLI 工具，输入图片路径，输出 Markdown 或 JSON 证据包。
- `textvision-fallback`：hook 辅助工具，根据外部传入的模型能力信息或图片输入失败错误，决定直传图片还是替换成文本上下文。
- `skills/textvision`：给 Claude Code、Codex 和其他支持 Skill 的 agent 使用的工作流封装。
- `.codex-plugin/plugin.json`：Codex 插件清单。

TextVision 的核心能力由本地 CLI 提供；Skill 和插件清单负责把这套能力接入 agent 工作流。

## 工作方式

1. 用户提供本地图片路径，或 agent 在消息里检测到本地图片路径。
2. 如果 agent 已经知道当前模型支持图片，图片可以直接传给模型。
3. 如果模型是纯文本模型、图片输入不可用，或图片输入失败，`textvision` 会在本地提取 OCR/SVG 文本。
4. 输出证据包包含文件信息、提取文本、可用时的置信度、确认事实、局限性，以及不要编造非文本视觉细节的回答指令。

TextVision 不会主动探测所有模型是否有视觉能力。自动 fallback 依赖 agent 或 hook 传入 `model_supports_images`，或者依赖上一轮图片输入失败时返回的错误，例如 “image input not supported”。

示例：

```text
输入图片：
  一张截图，显示 “Error: connection refused on port 3000”

证据包：
  - 提取文本："Error: connection refused on port 3000"
  - 文件名、格式、大小、尺寸
  - 确认事实
  - 局限性和回答指令

结果：
  纯文本模型可以根据错误文本推理，而不是假装自己看到了图片。
```

## 隐私

OCR 在本机运行。这个项目不会上传图片文件，不调用云端 OCR API，不需要 API key，也没有调用次数限制。

外部 agent 如果会先把原图发给云端模型，那是该 agent 自己的行为，不是 TextVision 的行为。需要避免这种情况时，可以直接运行 `textvision`，或让 agent 先走 fallback 工作流。

## 支持的输入

位图图片：

- `.png`
- `.jpg` / `.jpeg`
- `.webp`
- `.bmp`
- `.tiff` / `.tif`
- `.gif`

矢量/文本图片：

- `.svg` 会直接按 XML/text 解析，不走 OCR。

## OCR 后端

| 平台 | 默认后端 | 说明 |
| --- | --- | --- |
| macOS | Apple Vision OCR | 通过 Swift 调用系统内置 Vision 框架。 |
| Windows | Windows OCR | 通过 PowerShell 调用系统内置 Windows OCR API。 |
| Linux | PaddleOCR | Linux 没有统一内置 OCR，所以安装脚本默认安装 PaddleOCR。 |
| 任意平台 | Tesseract | 如果已安装，可以作为 fallback 或手动指定后端。 |
| 任意平台 | PaddleOCR | 可选高精度 OCR 后端。 |

SVG 文本提取是独立路径，不使用 OCR 后端。

## 安装

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash
```

默认安装内容：

- 本地运行时：`~/.textvision/`
- CLI：`~/.local/bin/textvision`
- Hook 辅助命令：`~/.local/bin/textvision-fallback`

默认不安装任何 agent Skill。

安装 Claude Code Skill：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target claude
```

安装 Codex Skill：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target codex
```

安装完成后，重启对应 agent 应用。

## 快速验证

用自带示例 SVG 跑一遍 CLI：

```bash
textvision ~/.textvision/testdata/sample.svg --json
```

如果输出里能看到下面两行，说明命令已经安装成功，并且可以提取文本：

```text
WebSocket handshake timeout
Reconnecting...
```

Windows、自定义路径、PaddleOCR、手动 clone 等场景见 [INSTALL.zh-CN.md](INSTALL.zh-CN.md)。

## 手动 CLI 用法

`CLI` 指的是终端命令。Claude Code、Codex 或其他 agent 已自动触发 `textvision` Skill 时，无需手动运行 CLI。

适合直接使用 CLI 的场景：

- agent 没有自动触发 Skill。
- 需要先把图片转换成文字，再复制给 DeepSeek 或其他纯文本模型。

将下面命令里的 `screenshot.png` 替换为实际图片路径。

```bash
# 最常用：把图片转成 Markdown 证据包
textvision screenshot.png

# 带上具体问题
textvision error.png --question "为什么构建失败了？"

# 输出 JSON，供脚本或 hook 使用
textvision screenshot.png --json
```

输出里的核心字段是 `context_for_text_model`。手动提交给 DeepSeek 时，复制这段内容即可。

### 高级 CLI 选项

默认 OCR 不理想，或需要调试后端时，再指定这些参数。

```bash
# 禁用 OCR，只返回文件信息和局限性
textvision screenshot.png --ocr-backend none

# 强制指定 OCR 后端
textvision screenshot.png --ocr-backend native
textvision screenshot.png --ocr-backend apple_vision
textvision screenshot.png --ocr-backend windows_ocr
textvision screenshot.png --ocr-backend paddleocr
textvision screenshot.png --ocr-backend tesseract
```

语言提示也属于高级选项：

```bash
textvision screenshot.png --vision-languages en-US,zh-Hans,ja-JP
textvision screenshot.png --windows-lang zh-Hans
textvision screenshot.png --tesseract-lang eng+chi_sim
```

## Skill 用法

使用 `--target claude`、`--target codex` 或其他 Skill 目标安装后，支持 Skill 的 agent 可以加载 `textvision`。

自动触发是 best-effort。agent 看到本地图片路径，并且已知当前模型是纯文本模型或图片输入已经失败时，Skill 可以被隐式调用。如果模型图片能力未知，但 agent 可以直接发送图片，预期流程是先尝试直传图片；只有直传失败后，才 fallback 到 `textvision`。

在 Claude Code 或类似 agent 里，可以这样提示：

```text
Use textvision to process ./testdata/sample.svg, then tell me what error text it contains.
```

在 DeepSeek 或其他纯文本模型所在的 agent 里，预期工作流是：

1. agent 看到图片路径。
2. `textvision` Skill 指示 agent 运行 `textvision <image_path>`。
3. agent 基于 `context_for_text_model` 回答，而不是基于想象的视觉细节回答。

agent 未自动触发 Skill 时，可以直接运行 CLI，然后把输出粘贴给模型。

当前触发边界：

- 最适合本地图片路径，或 agent 能暴露为本地路径的上传文件。
- 不会自己下载远程图片 URL。
- metadata-only 请求不应触发。
- 不能强制所有 agent 使用 Skill；宿主 agent 必须支持 Skills 和隐式调用。

## Hook 用法

`textvision-fallback` 从 stdin 读取 JSON，并返回一个 JSON action。它不会自己探测模型能力，而是根据 `model_supports_images` 或 `last_error` 判断。

已知模型不支持图片：

```bash
echo '{"message":"Check ./error.png","model_supports_images":false}' | textvision-fallback
```

模型图片能力未知：

```bash
echo '{"message":"Check ./error.png","model_supports_images":null}' | textvision-fallback
```

能力未知时，hook 会返回 `try_direct_first`。如果直传图片失败，可以带上 `last_error` 再调用一次：

```bash
echo '{"message":"Check ./error.png","model_supports_images":null,"last_error":"image input not supported"}' | textvision-fallback
```

hook 会识别常见英文和中文的图片不支持错误，例如 “image input not supported” 和 “不支持图片输入”。

## 输出结构

JSON 输出包含：

- `file_info`：路径、文件名、扩展名、大小、修改时间、可用时的尺寸。
- `available_backends`：检测到的提取后端。
- `requested_ocr_backend`：请求使用的 OCR 策略。
- `extraction_methods`：实际使用的提取方式。
- `extracted_text`：文本条目，包含来源、置信度和可用时的位置框。
- `confirmed_facts`：提取结果支持的事实。
- `uncertainties`：局限性和 OCR 无法确定的内容。
- `context_for_text_model`：给纯文本模型使用的主文本块。
- `backend_errors`：如果后端 fallback 失败，会记录失败信息。

## 局限性

- 这是 OCR 和 SVG 文本提取，不是完整视觉理解。
- 非文本物体、布局含义、图表、手写字、UI 状态、颜色、情绪和视觉风格都可能被遗漏。
- OCR 准确率取决于图片清晰度、语言支持、字体、方向和后端。
- Skill 封装不能强制所有 agent 使用这个工作流。有些工具需要重启或显式提示。
- 自动 fallback 依赖模型能力信息或可识别的图片输入错误；它不是通用的模型视觉能力探测器。
- Windows 原生 OCR 依赖系统 OCR 支持和已安装语言包。

## 故障排查

`textvision: command not found`

把 `~/.local/bin` 加入 `PATH`，然后重启 shell 或 agent 应用。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Claude Code/Codex 里 Skill 没触发

- 安装后重启 agent 应用。
- 确认 Skill 文件存在于 `~/.claude/skills/textvision/` 或 `~/.codex/skills/textvision/`。
- 显式提示：`Use textvision to process <image_path>`。

OCR 没提取到文本

- 换更清晰的图片，或裁剪到文字区域。
- 试试 PaddleOCR：`bash install.sh --with-paddleocr`，然后运行 `textvision image.png --ocr-backend paddleocr`。
- 对 SVG，确认文字是真正的 SVG text，而不是已经转成 outline/path。

macOS 提示缺少 Swift

安装 Xcode Command Line Tools：

```bash
xcode-select --install
```

Windows OCR 失败

- 用普通用户 PowerShell 运行，不要在受限环境里运行。
- 检查 Windows OCR 和对应语言包是否可用。
- 可以试试 `.\install.ps1 -WithPaddleOCR`，然后强制使用 PaddleOCR。

## 开发

安装开发依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

运行测试：

```bash
python -m pytest -q
python -m py_compile scripts/textvision.py hooks/textvision_fallback.py
```

本地 smoke test：

```bash
python scripts/textvision.py testdata/sample.svg --json
```

## 许可

MIT
