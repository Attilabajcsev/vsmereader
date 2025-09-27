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
    if (!confirm('Slet denne rapport?')) return;
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

<!-- Visual refresh only: keep existing behavior, remove hardcoded labels -->
<div class="bg-base-200/60 border-b">
  <div class="mx-auto max-w-6xl px-4 py-8">
    <h1 class="text-xl font-semibold">Portefølje</h1>

    <div class="mt-4 rounded-box border border-base-300 bg-base-100 p-6 shadow-md">
      <form class="mx-auto max-w-3xl flex items-stretch gap-2" onsubmit={(e) => { e.preventDefault(); loadReports(); }}>
        <input class="input input-bordered input-lg w-full" placeholder="Søg i portefølje (virksomhed eller år)" bind:value={q} />
        <button class="btn btn-neutral btn-lg" type="submit">Søg</button>
      </form>
    </div>
  </div>
</div>

<div class="px-4 pt-8 pb-6 bg-base-200/40 min-h-screen">
  <div class="mx-auto max-w-6xl">
    <div class="flex items-center justify-between">
      <div class="text-lg font-medium">Fandt {reports.length} resultat{reports.length === 1 ? '' : 'er'}</div>
    </div>

    {#if reports.length === 0}
      <div class="mt-4 text-sm opacity-75">Ingen rapporter matcher din søgning.</div>
    {:else}
      <div class="mt-4 space-y-3">
        {#each reports as r}
          <div class="rounded-box border border-base-300 bg-base-100 p-4 shadow-md hover:shadow-lg transition">
            <div class="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
              <div class="min-w-0 space-y-1">
                <div class="text-base font-semibold truncate">{r.company?.name || '—'}</div>
                <div class="text-xs opacity-70 truncate">Enhed: {r.entity || '—'}</div>
                <div class="text-xs opacity-70">Rapporteringsperiode: {formatPeriod(r.reporting_period)}</div>
                <div class="text-xs opacity-70">Oprettet: {formatDate(r.created_at)}</div>
              </div>
              <div class="flex items-start md:items-center gap-2 md:justify-end">
                <span class="badge badge-outline">År {r.reporting_year || '—'}</span>
                <span class={`badge ${r.status === 'validated' ? 'badge-success' : r.status === 'failed' ? 'badge-error' : ''}`}>
                  {r.status === 'validated' ? 'valideret' : r.status === 'failed' ? 'fejlet' : r.status === 'processing' ? 'behandler' : r.status}
                </span>
                <button class="btn btn-ghost btn-sm" onclick={() => goto(`/reports/${r.id}`)}>Åbn</button>
                <a class="btn btn-ghost btn-sm" href={`/api/reports/${r.id}/document/`} target="_blank">Inspicer</a>
                <button class="btn btn-error btn-sm" disabled={!!deleting[r.id]} onclick={() => onDelete(r.id)}>Slet</button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>


