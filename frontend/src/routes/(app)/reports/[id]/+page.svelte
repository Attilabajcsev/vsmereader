<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  let report: any = $state(null);
  let polling: any = $state(null);
  let facts: any[] = $state([]);
  let factsCount: number = $state(0);
  let summary: any = $state(null);
  let q: string = $state('');
  let pageNum: number = $state(1);
  let pageSize: number = $state(50);
  let deleteBusy: boolean = $state(false);

  function getId(): string {
    const m = globalThis.location?.pathname.match(/\/reports\/(\d+)/);
    return m ? m[1] : '';
  }

  async function load() {
    const id = getId();
    if (!id) return;
    const res = await fetch(`../../api/reports/${id}/`, { credentials: 'include' });
    if (res.ok) {
      report = await res.json();
    } else {
      report = null;
    }
  }

  async function onDelete() {
    const id = getId();
    if (!id) return;
    if (!confirm('Delete this report?')) return;
    deleteBusy = true;
    try {
      const res = await fetch(`../../api/reports/${id}/delete/`, { method: 'DELETE', credentials: 'include' });
      if (res.ok) {
        goto('/portfolio');
      }
    } finally {
      deleteBusy = false;
    }
  }

  function startPolling() {
    stopPolling();
    polling = setInterval(async () => {
      await load();
      if (report && report.status !== 'processing') {
        stopPolling();
        loadFacts();
        loadSummary();
      }
    }, 2000);
  }

  function stopPolling() {
    if (polling) clearInterval(polling);
    polling = null;
  }

  $effect(() => {
    load().then(() => {
      if (report && report.status === 'processing') startPolling();
      if (report && report.status !== 'processing') {
        loadFacts();
        loadSummary();
      }
    });
    return stopPolling;
  });

  async function loadFacts() {
    const id = getId();
    if (!id) return;
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    params.set('page', String(pageNum));
    params.set('page_size', String(pageSize));
    const res = await fetch(`../../api/reports/${id}/facts/?${params.toString()}`, { credentials: 'include' });
    if (res.ok) {
      const data = await res.json();
      facts = data.results;
      factsCount = data.count;
    }
  }

  $effect(() => {
    loadFacts();
  });

  async function loadSummary() {
    const id = getId();
    if (!id) return;
    const res = await fetch(`../../api/reports/${id}/summary/`, { credentials: 'include' });
    if (res.ok) {
      summary = await res.json();
    } else {
      summary = null;
    }
  }


  function inspectInline() {
    const id = getId();
    if (!id) return;
    window.open(`../../api/reports/${id}/document/`, '_blank');
  }
</script>

<div class="p-6 bg-base-200/40 min-h-screen">
  <div class="mx-auto max-w-5xl space-y-6">
    <div class="flex items-start justify-between">
      <div>
        <button class="btn btn-ghost" onclick={() => goto('/portfolio')}>← Tilbage</button>
        <h1 class="text-2xl font-semibold mt-2">Rapport #{report?.user_report_number ?? report?.id ?? ''}</h1>
        <div class="text-sm opacity-80 mt-1">
          <span>Virksomhed: {report?.company?.name || '—'}</span>
          <span class="mx-2">•</span>
          <span>År: {report?.reporting_year || '—'}</span>
        </div>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-error btn-sm" disabled={deleteBusy} onclick={onDelete}>Slet</button>
      </div>
    </div>

  {#if !report}
    <div>Indlæser…</div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2">
      <div class="rounded-box border border-base-300 bg-base-100 p-4 shadow-sm">
        <div class="text-sm opacity-80 space-y-1">
          <div>Enhed: {report.entity || '—'}</div>
          <div>Rapporteringsperiode: {report.reporting_period || '—'}</div>
          <div>Taksonomi version: {report.taxonomy_version || '—'}</div>
          <div>Status: <span class="badge {report.status === 'validated' ? 'badge-success' : report.status === 'failed' ? 'badge-error' : 'badge-ghost'}">
            {report.status === 'validated' ? 'valideret' : report.status === 'failed' ? 'fejlet' : report.status === 'processing' ? 'behandler' : report.status}
          </span></div>
          <div>Oprettet: {new Date(report.created_at).toLocaleString()}</div>
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          {#if report.original_file_url}
            <a class="btn btn-sm" href={`../../api/reports/${report.id}/download/original/`}>Download original iXBRL</a>
          {/if}
          {#if report.oim_json_file_url}
            <a class="btn btn-sm" href={`../../api/reports/${report.id}/download/oim-json/`}>Download udtrukket JSON</a>
          {/if}
          <button class="btn btn-sm" onclick={inspectInline}>Inspicer rapport</button>
        </div>
      </div>

      <div class="rounded-box border border-base-300 bg-base-100 p-4 shadow-sm">
        {#if report.status === 'validated'}
          <h2 class="text-lg font-semibold mb-2">vSME ESG Sammendrag</h2>
          {#if summary}
            <div class="text-sm opacity-80 mb-2">Enhed: {summary.entity || '—'} • Periode: {summary.reporting_period || '—'} • Fakta: {summary.fact_count}</div>
            <ul class="space-y-1">
              {#each summary.items as item}
                <li class="flex items-center justify-between">
                  <span>{item.label}</span>
                  <span class="badge {item.present ? 'badge-success' : 'badge-ghost'}" title={item.value || ''}>
                    {item.present && item.value ? item.value : '—'}
                  </span>
                </li>
              {/each}
            </ul>
          {:else}
            <div class="opacity-70 text-sm">No summary available.</div>
          {/if}
        {:else if report.status === 'failed'}
          <div class="text-error">Failed</div>
          {#if report.failure_reason}
            <pre class="whitespace-pre-wrap text-xs opacity-80">{report.failure_reason}</pre>
          {/if}
        {:else}
          <div>Processing…</div>
        {/if}
      </div>
    </div>

    <div class="mt-6 space-y-3">
      <div class="flex items-center gap-3">
        <input class="input input-bordered w-full max-w-xs" placeholder="Filter facts (concept/value)" bind:value={q} onchange={() => { pageNum = 1; loadFacts(); }} />
        <button class="btn" onclick={() => { pageNum = 1; loadFacts(); }}>Apply</button>
      </div>
      <div class="overflow-x-auto rounded-box border border-base-300 bg-base-100 shadow-sm" id="facts-table">
        <table class="table">
          <thead>
            <tr>
              <th>Concept</th>
              <th>Value</th>
              <th>Datatype</th>
              <th>Unit</th>
              <th>Context</th>
            </tr>
          </thead>
          <tbody>
            {#if facts.length === 0}
              <tr><td colspan="5">No datapoints match your search.</td></tr>
            {:else}
              {#each facts as f}
                <tr>
                  <td>{f.concept}</td>
                  <td class="max-w-[420px] truncate" title={f.value}>{f.value}</td>
                  <td>{f.datatype}</td>
                  <td>{f.unit}</td>
                  <td>{f.context}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn" onclick={() => { if (pageNum > 1) { pageNum -= 1; loadFacts(); } }} disabled={pageNum <= 1}>Prev</button>
        <div>Page {pageNum} / {Math.max(1, Math.ceil(factsCount / pageSize))}</div>
        <button class="btn" onclick={() => { const max = Math.max(1, Math.ceil(factsCount / pageSize)); if (pageNum < max) { pageNum += 1; loadFacts(); } }} disabled={pageNum >= Math.max(1, Math.ceil(factsCount / pageSize))}>Next</button>
      </div>
    </div>
  {/if}
  </div>
</div>


