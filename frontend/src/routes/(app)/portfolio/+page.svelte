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

  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleDateString();
  }

  function formatPeriod(p: string | null | undefined): string {
    if (!p) return '—';
    if (p.includes('/')) {
      const [a, b] = p.split('/');
      return `${(a || '').split('T')[0]} to ${(b || '').split('T')[0]}`;
    }
    return p.split('T')[0] || p;
  }

  $effect(() => { loadReports(); });
</script>

<div class="p-6 bg-base-200/40">
  <div class="mx-auto max-w-6xl space-y-6">
    <!-- Title -->
    <h1 class="text-2xl font-semibold">CVR‑style ESG Portfolio</h1>

    <!-- Search block (company-focused) -->
    <div class="rounded-box border bg-base-100 p-4">
      <form class="flex items-center gap-3" onsubmit={(e) => { e.preventDefault(); loadReports(); }}>
        <div class="flex-1">
          <input class="input input-bordered w-full" placeholder="Search company name" bind:value={q} />
        </div>
        <button class="btn btn-neutral" type="submit">Search</button>
      </form>
    </div>

    <!-- Results header -->
    <div class="flex items-center justify-between">
      <div class="text-lg font-medium">{reports.length} result{reports.length === 1 ? '' : 's'}</div>
    </div>

    <!-- Results list (cards) -->
    {#if reports.length === 0}
      <div class="text-sm opacity-75">No reports match your search.</div>
    {:else}
      <div class="space-y-3">
        {#each reports as r}
          <div class="rounded-box border bg-base-100 p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="text-base font-semibold truncate">{r.company?.name || '—'}</div>
                <div class="text-xs opacity-70 truncate">Entity: {r.entity || '—'}</div>
              </div>
              <div class="flex items-center gap-2">
                <span class="badge badge-ghost">Year {r.reporting_year || '—'}</span>
                <span class="badge {r.status === 'validated' ? 'badge-success' : r.status === 'failed' ? 'badge-error' : ''}">{r.status}</span>
              </div>
            </div>
            <div class="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
              <div>
                <div class="opacity-60 text-xs">Reporting period</div>
                <div>{formatPeriod(r.reporting_period)}</div>
              </div>
              <div>
                <div class="opacity-60 text-xs">Created</div>
                <div>{formatDate(r.created_at)}</div>
              </div>
              <div class="flex items-center gap-2 justify-start sm:justify-end">
                <button class="btn btn-ghost btn-sm" onclick={() => goto(`/reports/${r.id}`)}>Open</button>
                <button class="btn btn-error btn-sm" disabled={!!deleting[r.id]} onclick={() => onDelete(r.id)}>Delete</button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>


