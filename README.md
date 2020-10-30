# Google WiFi Home Assistant Integration

<a target="_blank" href="https://www.buymeacoffee.com/djtimca"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy me a coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;"></a> [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)


This integration provides control and monitoring of the Google WiFi system within Home Assistant.

More details to come.

### Install through HACS:

Add a custom repository in HACS pointed to https://github.com/djtimca/hagooglewifi

The new integration for Google WiFi should appear under your integrations tab.

Click Install and restart Home Assistant.

### Install manually:

Copy the contents found in https://github.com/djtimca/hagooglewifi/custom_components/rocketlaunchlive to your custom_components folder in Home Assistant.

Restart Home Assistant.

## Configure the integration:

To install this integration you will need a Google Refresh Token which you can get by following the instructions at: https://www.angelod.com/onhubauthtool

Note that using the Chrome Plugin is much easier.

Once installed, restart Home Assistant and go to Configuration -> Integrations and click the + to add a new integration.

Search for Google WiFi and you will see the integration available.

Enter the refresh token in the integration configuration screen and hit submit.

Enjoy!