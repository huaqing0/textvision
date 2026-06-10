# Image Context Bridge

[English](README.md)

Image Context Bridge 是一个本地工作流，用来帮助纯文本模型或不支持图片输入的模型处理图片。它会把图片文件转换成结构化的文本证据包，让模型只基于 OCR 文本、文件信息和明确的局限性来回答。

它适合把 DeepSeek、本地大模型或其他纯文本 agent 用在截图、错误弹窗、SVG、图片文件等场景里，避免模型在看不到图片时编造视觉细节。

## 包含什么

- `image2context`：CLI 工具，输入图片路径，输出 Markdown 或 JSON 证据包。
- `auto-image-fallback`：hook 辅助工具，根据模型是否支持图片来决定直传图片还是替换成文本上下文。
- `skills/image-context`：给 Claude Code、Codex 和其他支持 Skill 的 agent 使用的工作流封装。

Skill 本身只是工作流说明。真正执行 OCR 和文本提取的是本地 `image2context` 命令。

## 工作方式

1. 用户提供图片路径，或 agent 在消息里检测到图片路径。
2. 如果当前模型支持图片，图片可以直接传给模型。
3. 如果模型是纯文本模型，或图片输入失败，`image2context` 会在本地提取 OCR/SVG 文本。
4. 输出证据包包含文件信息、提取文本、可用时的置信度、确认事实、局限性，以及不要编造非文本视觉细节的回答指令。

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

如果你使用的外部 agent 会先把原图发给云端模型，那是该 agent 自己的行为，不是 Image Context Bridge 的行为。想避免这种情况，可以直接运行 `image2context`，或让 agent 先走 fallback 工作流。

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

克隆仓库后，在项目目录里运行安装脚本。

macOS 或 Linux：

```bash
bash install.sh
```

Windows PowerShell：

```powershell
.\install.ps1
```

选装 PaddleOCR：

```bash
bash install.sh --with-paddleocr
```

```powershell
.\install.ps1 -WithPaddleOCR
```

如果 Linux 上只想使用 metadata/SVG 提取，或想自己管理 OCR 后端，可以跳过 PaddleOCR：

```bash
bash install.sh --no-paddleocr
```

安装脚本会创建：

- `~/.image-context-bridge/`：本地应用文件和 Python 虚拟环境。
- `~/.local/bin/image2context`
- `~/.local/bin/auto-image-fallback`
- `~/.agents/skills/image-context/`
- `~/.claude/skills/image-context/`
- `~/.codex/skills/image-context/`

请确认 `~/.local/bin` 在 `PATH` 里。安装后重启 Claude Code、Codex 或其他 agent 应用，让它重新加载 Skill。

## 安装后自检

这一段不是日常用法，只是用仓库里的示例文件确认安装成功。

请先进入仓库根目录，因为 `testdata/sample.svg` 是仓库自带的测试文件：

```bash
cd image-context-bridge
```

第一步，确认 `image2context` 命令能运行：

```bash
image2context testdata/sample.svg --json
```

如果输出里能看到下面两行，说明 CLI 可以读取图片并提取文本：

```text
WebSocket handshake timeout
Reconnecting...
```

第二步，确认 fallback hook 能运行：

```bash
echo '{"message":"Please analyze ./testdata/sample.svg","model_supports_images":false}' | auto-image-fallback
```

这条命令是在模拟“当前模型不支持图片”。如果输出里的 `action` 是 `replace_with_context`，说明 hook 会把图片替换成文本证据包：

```json
{"action":"replace_with_context","contexts":["..."]}
```

## 手动 CLI 用法

`CLI` 指的是终端命令。通常你不需要手动用它；如果 Claude Code、Codex 或其他 agent 已经自动触发 `image-context` Skill，它会自己调用。

你需要手动用 CLI 的场景主要有两个：

- agent 没有自动触发 Skill。
- 你想先把一张图片转换成文字，再复制给 DeepSeek 或其他纯文本模型。

把下面命令里的 `screenshot.png` 换成你的真实图片路径。

```bash
# 最常用：把图片转成 Markdown 证据包
image2context screenshot.png

# 如果你有具体问题，把问题也写进去
image2context error.png --question "为什么构建失败了？"

# 如果你要给脚本或 hook 使用，输出 JSON
image2context screenshot.png --json
```

输出里的核心字段是 `context_for_text_model`。如果你手动给 DeepSeek 用，复制这段内容即可。

### 高级 CLI 选项

一般用户可以跳过这一段。只有默认 OCR 不理想，或你在调试后端时才需要指定这些参数。

```bash
# 禁用 OCR，只返回文件信息和局限性
image2context screenshot.png --ocr-backend none

# 强制指定 OCR 后端
image2context screenshot.png --ocr-backend native
image2context screenshot.png --ocr-backend apple_vision
image2context screenshot.png --ocr-backend windows_ocr
image2context screenshot.png --ocr-backend paddleocr
image2context screenshot.png --ocr-backend tesseract
```

语言提示也属于高级选项：

```bash
image2context screenshot.png --vision-languages en-US,zh-Hans,ja-JP
image2context screenshot.png --windows-lang zh-Hans
image2context screenshot.png --tesseract-lang eng+chi_sim
```

## Skill 用法

安装后，支持 Skill 的 agent 可以加载 `image-context`。

在 Claude Code 或类似 agent 里，可以这样提示：

```text
Use image-context to process ./testdata/sample.svg, then tell me what error text it contains.
```

在 DeepSeek 或其他纯文本模型所在的 agent 里，预期工作流是：

1. agent 看到图片路径。
2. `image-context` Skill 指示 agent 运行 `image2context <image_path>`。
3. agent 基于 `context_for_text_model` 回答，而不是基于想象的视觉细节回答。

如果 agent 没有自动触发 Skill，可以自己运行 CLI，然后把输出粘贴给模型。

## Hook 用法

`auto-image-fallback` 从 stdin 读取 JSON，并返回一个 JSON action。

已知模型不支持图片：

```bash
echo '{"message":"Check ./error.png","model_supports_images":false}' | auto-image-fallback
```

模型图片能力未知：

```bash
echo '{"message":"Check ./error.png","model_supports_images":null}' | auto-image-fallback
```

能力未知时，hook 会返回 `try_direct_first`。如果直传图片失败，可以带上 `last_error` 再调用一次：

```bash
echo '{"message":"Check ./error.png","model_supports_images":null,"last_error":"image input not supported"}' | auto-image-fallback
```

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
- Windows 原生 OCR 依赖系统 OCR 支持和已安装语言包。

## 故障排查

`image2context: command not found`

把 `~/.local/bin` 加入 `PATH`，然后重启 shell 或 agent 应用。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Claude Code/Codex 里 Skill 没触发

- 安装后重启 agent 应用。
- 确认 Skill 文件存在于 `~/.claude/skills/image-context/` 或 `~/.codex/skills/image-context/`。
- 显式提示：`Use image-context to process <image_path>`。

OCR 没提取到文本

- 换更清晰的图片，或裁剪到文字区域。
- 试试 PaddleOCR：`bash install.sh --with-paddleocr`，然后运行 `image2context image.png --ocr-backend paddleocr`。
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
python -m py_compile scripts/image2context.py hooks/auto_image_fallback.py
```

本地 smoke test：

```bash
python scripts/image2context.py testdata/sample.svg --json
```

## 许可

MIT
