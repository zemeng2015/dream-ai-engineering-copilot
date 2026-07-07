// SPDX-License-Identifier: Apache-2.0

export interface RepoFolderEntry {
  name: string;
  path: string;
  fileCount: number;
}

export interface RepoBreadcrumb {
  label: string;
  path: string;
}
