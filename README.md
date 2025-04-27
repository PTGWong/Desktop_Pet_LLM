# 桌面宠物 (Desktop Pet)

这是一个使用Python和PyQt5实现的桌面宠物程序，可以显示GIF动画，并通过DeepSeek LLM API实现与宠物的对话功能。

## 功能特点

- 显示可爱的小豆泥GIF动画
- 支持切换不同的动作GIF
- 通过LLM实现与宠物的对话交互
- 可拖动宠物在桌面上移动
- 自定义宠物角色设定

## 安装依赖

```bash
# 创建conda环境
conda create -n desktop_pet python=3.8
conda activate desktop_pet

# 安装依赖包
pip install PyQt5 openai
```

## 使用方法

1. 将GIF图像放入`pic`文件夹中，命名为对应的动作名称，如`idle.gif`、`happy.gif`等
2. 运行程序：

```bash
python main.py
```

3. 右键点击宠物可以打开菜单：
   - 切换动作：选择不同的GIF动画
   - 与宠物对话：输入文字与宠物进行对话
   - 设置：配置API密钥等
   - 退出：关闭程序

## 配置说明

首次运行程序会创建`config.json`配置文件，包含以下内容：

```json
{
    "openai_api_key": "",
    "openai_api_base": "https://api.deepseek.com/v1/chat/completions",
    "pet_prompt": "你是一个可爱的桌面宠物小豆泥，性格活泼开朗，说话方式可爱，喜欢用颜文字和表情。请用简短的语言回答用户的问题。",
    "actions": ["idle", "happy", "sad", "sleep"],
    "model": "deepseek-chat"
}
```

- `openai_api_key`：DeepSeek API密钥
- `openai_api_base`：API基础URL
- `pet_prompt`：宠物角色设定
- `actions`：可用的动作列表
- `model`：使用的模型名称

## 自定义宠物

1. 准备不同动作的GIF图像，放入`pic`文件夹
2. 在`config.json`中的`actions`数组中添加对应的动作名称
3. 修改`pet_prompt`可以改变宠物的性格和对话风格