# Home Assistant n8n Conversation Agent

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]][license]
<!-- Add other shields if you like: HACS, build status etc. -->

This custom integration for Home Assistant allows you to use an n8n webhook as a conversation agent within Home Assistant's voice assistant pipelines.

**This integration requires:**
*   Home Assistant version 2024.1.0 or newer.
*   An n8n instance with a webhook workflow configured.

## Features
*   Sends text input from Home Assistant's voice pipeline to a specified n8n webhook.
*   Receives a text response from n8n and relays it back to the voice pipeline.
*   Configurable via the Home Assistant UI.

## n8n Workflow Setup
Your n8n workflow should:
1.  Start with a **Webhook node** (HTTP Method: `POST`).
    *   It will receive a JSON payload like:
        ```json
        {
            "text": "user's voice command",
            "language": "en",
            "conversation_id": "some-uuid",
            "device_id": "your_device_id_if_any",
            "context": { /* ... Home Assistant context ... */ }
        }
        ```
2.  Process this input.
3.  End with a **Respond to Webhook node** (or respond directly from the Webhook node) that sends back a JSON payload like:
    ```json
    {
        "response_text": "The answer from your n8n workflow."
    }
    ```
Copy the **Production URL** from your n8n Webhook node.

## Installation

### Method 1: HACS (Recommended)
1.  Ensure you have [HACS (Home Assistant Community Store)](https://hacs.xyz/) installed.
2.  In HACS, go to "Integrations".
3.  Click the three dots in the top right, select "Custom repositories".
4.  Enter `https://github.com/[YOUR_USERNAME]/[YOUR_REPOSITORY_NAME]` as the repository URL.
5.  Select "Integration" as the category.
6.  Click "Add".
7.  Find "n8n Conversation Agent" in the list and click "Install".
8.  Restart Home Assistant.

### Method 2: Manual Installation
1.  Download the latest release ZIP from the [Releases page](https://github.com/[YOUR_USERNAME]/[YOUR_REPOSITORY_NAME]/releases) of this repository.
2.  Extract the `n8n_conversation` folder from the ZIP.
3.  Copy the `n8n_conversation` folder into your Home Assistant's `<config_directory>/custom_components/` directory.
4.  Restart Home Assistant.

## Configuration
1.  Go to Settings -> Devices & Services -> Add Integration.
2.  Search for "n8n Conversation Agent" and select it.
3.  Enter your n8n Webhook URL when prompted.
4.  (Optional but Recommended) Go to Settings -> Voice assistants. Select your Assist pipeline (or create one) and choose "n8n Conversation Agent" as the conversation agent.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

---