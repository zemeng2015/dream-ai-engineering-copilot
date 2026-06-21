export class JobListComponent { columns = ['name', 'owner', 'workflow', 'status']; statusLabel(status: string): string { return status.toLowerCase().replace('_', ' '); } }
