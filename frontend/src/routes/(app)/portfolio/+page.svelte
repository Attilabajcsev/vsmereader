<script lang="ts">
  import { goto } from '$app/navigation';
  let q: string = $state('');
  let reports: any[] = $state([]);
  let deleting: Record<number, boolean> = $state({});

  async function loadReports() {
    const url = q ? `api/reports/?q=${encodeURIComponent(q)}` : 'api/reports/';
    const res = await fetch(url, { credentials: 'include' });
    if (res.ok) {
      reports = await res.json();
    }
  }

  async function onDelete(id: number) {
    if (!confirm('Delete this report?')) return;
    deleting[id] = true;
    try {
      const res = await fetch(`/api/reports/${id}/delete/`, { method: 'DELETE', credentials: 'include' });
      if (res.ok) {
        await loadReports();
      }
    } finally {
      deleting[id] = false;
    }
  }

  $effect(() => { loadReports(); });
</script>

<div class="p-6">
  <div class="mx-auto max-w-6xl space-y-6">
    <h1 class="text-2xl font-semibold">Portfolio</h1>

    <form class="flex items-center gap-3" onsubmit={(e) => { e.preventDefault(); loadReports(); }}>
      <input class="input input-bordered w-full max-w-xs" placeholder="Filter by entity or period" bind:value={q} />
      <button class="btn btn-neutral" type="submit">Search</button>
    </form>

    {#if reports.length === 0}
      <div class="text-sm opacity-75">No reports found.</div>
    {:else}
      <div class="overflow-x-auto rounded border">
        <table class="table">
        <thead>
          <tr>
            <th>Company</th>
            <th>Year</th>
            <th>Entity</th>
            <th>Reporting Period</th>
            <th>Status</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each reports as r}
            <tr class="hover">
              <td>{r.company?.name || '—'}</td>
              <td>{r.reporting_year || '—'}</td>
              <td>{r.entity || '—'}</td>
              <td>{r.reporting_period || '—'}</td>
              <td>{r.status}</td>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td class="flex gap-2">
                <button class="btn btn-ghost btn-sm" onclick={() => goto(`/reports/${r.id}`)}>Open</button>
                <button class="btn btn-error btn-sm" disabled={!!deleting[r.id]} onclick={() => onDelete(r.id)}>Delete</button>
              </td>
            </tr>
          {/each}
        </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>


