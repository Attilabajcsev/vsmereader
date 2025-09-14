<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  let report: any = $state(null);
  let polling: any = $state(null);
  let facts: any[] = $state([]);
  let factsCount: number = $state(0);
  let q: string = $state('');
  let pageNum: number = $state(1);
  let pageSize: number = $state(50);

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

  function startPolling() {
    stopPolling();
    polling = setInterval(async () => {
      await load();
      if (report && report.status !== 'processing') stopPolling();
    }, 2000);
  }

  function stopPolling() {
    if (polling) clearInterval(polling);
    polling = null;
  }

  $effect(() => {
    load().then(() => {
      if (report && report.status === 'processing') startPolling();
      if (report && report.status !== 'processing') loadFacts();
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
</script>

<div class="p-6 space-y-6">
  <button class="btn btn-ghost" on:click={() => goto('/reports')}>← Back</button>

  {#if !report}
    <div>Loading…</div>
  {:else}
    <div class="space-y-2">
      <h1 class="text-2xl font-semibold">Report #{report.id}</h1>
      <div class="text-sm opacity-80">
        <div>Entity: {report.entity || '—'}</div>
        <div>Reporting Period: {report.reporting_period || '—'}</div>
        <div>Taxonomy Version: {report.taxonomy_version || '—'}</div>
        <div>Status: {report.status}</div>
        <div>Created: {new Date(report.created_at).toLocaleString()}</div>
      </div>
    </div>

    <div class="rounded border p-4">
      {#if report.status === 'validated'}
        <div class="text-success">Validated</div>
        {#if report.validation_summary}
          <pre class="whitespace-pre-wrap text-xs opacity-80">{report.validation_summary}</pre>
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

    <div class="flex gap-3">
      {#if report.original_file_url}
        <a class="btn" href={`../../api/reports/${report.id}/download/original/`}>Download original iXBRL</a>
      {/if}
      {#if report.oim_json_file_url}
        <a class="btn" href={`../../api/reports/${report.id}/download/oim-json/`}>Download extracted JSON</a>
      {/if}
    </div>

    <div class="mt-6 space-y-3">
      <div class="flex items-center gap-3">
        <input class="input input-bordered w-full max-w-xs" placeholder="Filter facts (concept/value)" bind:value={q} on:change={() => { pageNum = 1; loadFacts(); }} />
        <button class="btn" on:click={() => { pageNum = 1; loadFacts(); }}>Apply</button>
      </div>
      <div class="overflow-x-auto">
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
        <button class="btn" on:click={() => { if (pageNum > 1) { pageNum -= 1; loadFacts(); } }} disabled={pageNum <= 1}>Prev</button>
        <div>Page {pageNum} / {Math.max(1, Math.ceil(factsCount / pageSize))}</div>
        <button class="btn" on:click={() => { const max = Math.max(1, Math.ceil(factsCount / pageSize)); if (pageNum < max) { pageNum += 1; loadFacts(); } }} disabled={pageNum >= Math.max(1, Math.ceil(factsCount / pageSize))}>Next</button>
      </div>
    </div>
  {/if}
</div>


