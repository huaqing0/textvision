# 安装选项

README 保留常用安装命令。本文档列出其他安装参数。

## Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.ps1 | iex"
```

在 Windows 上安装 Claude Code Skill 封装：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command '$env:TEXTVISION_TARGET="claude"; irm https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.ps1 | iex'
```

## 其他 Skill 目标

安装到通用 agents Skill 目录：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target agents
```

一次安装到所有已知 Skill 目录：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --target all
```

## 自定义路径

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --app-dir "$HOME/Tools/textvision" --bin-dir "$HOME/bin"
```

使用自定义 Skill 根目录。安装器会创建 `<skill-root>/textvision`：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --skill-dir "$HOME/.claude/skills"
```

## PaddleOCR

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --with-paddleocr
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command '$env:TEXTVISION_WITH_PADDLEOCR="1"; irm https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.ps1 | iex'
```

Linux 如仅需 metadata/SVG 提取，或需要自行管理 OCR 后端，可以跳过 PaddleOCR：

```bash
curl -fsSL https://raw.githubusercontent.com/huaqing0/textvision/main/install-remote.sh | bash -s -- --no-paddleocr
```

## 手动 clone

```bash
git clone https://github.com/huaqing0/textvision.git
cd textvision
bash install.sh
```

```powershell
git clone https://github.com/huaqing0/textvision.git
cd textvision
.\install.ps1
```

## Hook 验证

这条命令用于模拟“当前模型不支持图片”。如果输出里的 `action` 是 `replace_with_context`，说明 hook 会把图片替换成文本证据包：

```bash
echo '{"message":"Please analyze ~/.textvision/testdata/sample.svg","model_supports_images":false}' | textvision-fallback
```

```json
{"action":"replace_with_context","contexts":["..."]}
```
