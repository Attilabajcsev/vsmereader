<script lang="ts">
  import { goto } from '$app/navigation';
  let companies: any[] = $state([]);
  let selectedCompanyId: string = $state('');
  let selectedYear: string = $state('');
  let uploading: boolean = $state(false);
  let uploadError: string | null = $state(null);
  let newCompanyName: string = $state('');
  let creatingCompany: boolean = $state(false);

  async function loadCompanies() {
    const res = await fetch('/api/companies/', { credentials: 'include' });
    if (res.ok) {
      companies = await res.json();
    }
  }

  async function createCompany() {
    const name = (newCompanyName || '').trim();
    if (!name) return;
    creatingCompany = true;
    try {
      const res = await fetch('/api/companies/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name })
      });
      if (res.ok || res.status === 201) {
        const c = await res.json();
        await loadCompanies();
        selectedCompanyId = String(c.id);
        newCompanyName = '';
      } else {
        uploadError = await res.text();
      }
    } finally {
      creatingCompany = false;
    }
  }

  async function onSubmit(ev: Event) {
    ev.preventDefault();
    const formEl = ev.target as HTMLFormElement;
    const fileInput = formEl.querySelector('#ixbrl-file') as HTMLInputElement;
    if (!fileInput?.files || fileInput.files.length === 0) { uploadError = 'Please choose a file'; return; }
    if (!selectedCompanyId) { uploadError = 'Please select or create a company'; return; }
    if (!selectedYear) { uploadError = 'Please enter a year'; return; }
    const formData = new FormData();
    formData.append('original_file', fileInput.files[0]);
    formData.append('company', selectedCompanyId);
    formData.append('reporting_year', selectedYear);
    uploadError = null;
    uploading = true;
    try {
      const res = await fetch('/api/reports/upload/', { method: 'POST', body: formData, credentials: 'include' });
      if (!res.ok) {
        const text = await res.text();
        uploadError = text || res.statusText;
      } else {
        const data = await res.json();
        goto(`/reports/${data.id}`);
      }
    } catch (e) {
      uploadError = 'Upload failed';
    } finally {
      uploading = false;
    }
  }

  $effect(() => { loadCompanies(); });
</script>

<div class="min-h-[80vh] grid place-items-center p-6">
  <div class="w-full max-w-lg rounded-box border bg-base-100 p-6 space-y-5">
    <h1 class="text-2xl font-semibold text-center">Submit report</h1>
    <form class="space-y-4" onsubmit={onSubmit}>
      {#if uploadError}
        <div class="alert alert-error"><span>{uploadError}</span></div>
      {/if}
      <div class="form-control">
        <div class="mb-1 text-sm font-medium">Company</div>
        <select id="company-select" class="select select-bordered w-full" bind:value={selectedCompanyId}>
          <option value="">Select company…</option>
          {#each companies as c}
            <option value={String(c.id)}>{c.name}</option>
          {/each}
        </select>
      </div>
      <div class="form-control">
        <div class="mb-1 text-sm font-medium">Or create company</div>
        <div class="flex gap-2">
          <input id="new-company" class="input input-bordered flex-1" placeholder="Acme Ltd" bind:value={newCompanyName} />
          <button class="btn" type="button" disabled={creatingCompany || !newCompanyName.trim()} onclick={createCompany}>
            {#if creatingCompany}
              <span class="loading loading-spinner loading-sm"></span>
            {:else}
              Create
            {/if}
          </button>
        </div>
      </div>
      <div class="form-control">
        <div class="mb-1 text-sm font-medium">Tax year</div>
        <input id="tax-year" class="input input-bordered w-36" type="number" min="1900" max="2100" placeholder="2024" bind:value={selectedYear} />
      </div>
      <div class="form-control">
        <div class="mb-1 text-sm font-medium">iXBRL file (.xhtml or .zip)</div>
        <input id="ixbrl-file" class="file-input file-input-bordered w-full" type="file" accept=".xhtml,.zip" />
      </div>
      <div class="pt-2">
        <button class="btn btn-primary w-full sm:w-auto" type="submit" disabled={uploading}>
          {#if uploading}
            <span class="loading loading-spinner loading-sm"></span> Uploading…
          {:else}
            Submit
          {/if}
        </button>
      </div>
    </form>
  </div>
  
</div>


