// SPDX-License-Identifier: Apache-2.0

import { Config } from '@remotion/cli/config';

Config.setOverwriteOutput(true);
Config.setPixelFormat('yuv420p');
Config.setVideoImageFormat('jpeg');
Config.setConcurrency(4);
