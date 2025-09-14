<script lang="ts">
  import { goto } from '$app/navigation';
  let q: string = $state('');
  let reports: any[] = $state([]);
  let uploading: boolean = $state(false);
  let uploadError: string | null = $state(null);
  let deleting: Record<number, boolean> = $state({});

  async function loadReports() {
    const url = q ? `api/reports/?q=${encodeURIComponent(q)}` : 'api/reports/';
    const res = await fetch(url, { credentials: 'include' });
    if (res.ok) {
      reports = await res.json();
    }
  }

  async function onUpload(ev: Event) {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    const fileInput = form.querySelector('input[type=file]') as HTMLInputElement;
    if (!fileInput?.files || fileInput.files.length === 0) return;
    const formData = new FormData();
    formData.append('original_file', fileInput.files[0]);
    uploadError = null;
    uploading = true;
    try {
      const res = await fetch('/api/reports/upload/', {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });
      if (!res.ok) {
        const text = await res.text();
        uploadError = text || res.statusText;
      } else {
        await loadReports();
      }
    } catch (e) {
      uploadError = 'Upload failed';
    } finally {
      uploading = false;
      (form.reset && form.reset());
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

  $effect(() => {
    loadReports();
  });
</script>

<div class="p-6 space-y-6">
  <h1 class="text-2xl font-semibold">Reports</h1>

  <form class="flex items-center gap-3" onsubmit={(e) => { e.preventDefault(); loadReports(); }}>
    <input class="input input-bordered w-full max-w-xs" placeholder="Filter by entity or period" bind:value={q} />
    <button class="btn btn-neutral" type="submit">Search</button>
  </form>

  <form class="flex items-center gap-3" onsubmit={onUpload}>
    <input class="file-input file-input-bordered" type="file" accept=".xhtml,.zip" />
    <button class="btn btn-primary" disabled={uploading}>
      {#if uploading}
        <span class="loading loading-spinner loading-sm"></span> Uploading…
      {:else}
        Upload
      {/if}
    </button>
    {#if uploadError}
      <span class="text-error">{uploadError}</span>
    {/if}
  </form>

  {#if reports.length === 0}
    <div class="text-sm opacity-75">You haven’t uploaded any reports.</div>
  {:else}
    <div class="overflow-x-auto">
      <table class="table">
        <thead>
          <tr>
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


