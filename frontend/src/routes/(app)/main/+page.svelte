<script lang="ts">
    import { goto } from '$app/navigation';
    $effect(() => { goto('/login'); });
    // Legacy page removed; send users to login (which will redirect if already authed)
</script>

<div class="p-6">Redirecting to Portfolio… <a class="link" href="/portfolio">Go now</a></div>
