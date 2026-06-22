// SPDX-License-Identifier: Apache-2.0

export class JobListComponent { columns = ['name', 'owner', 'workflow', 'status']; statusLabel(status: string): string { return status.toLowerCase().replace('_', ' '); } }
