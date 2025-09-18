<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	let { data, children } = $props();
	let nonProtectedRoutes: string[] = ['/', '/login', '/register', '/login-oauth', '/oauth-google'];
</script>

<div class="flex min-h-screen flex-col">
	<div class="navbar bg-base-100 border-base-300 border shadow-md">
		<div class="navbar-start">
			<span class="btn btn-ghost text-xl pointer-events-none select-none">IXBRL VSME Reader</span>
			{#if data.authed}
				<a class="btn btn-ghost" href="/submit">Submit report</a>
				<a class="btn btn-ghost" href="/portfolio">Portfolio</a>
				<a class="btn btn-ghost" href="/insights">Insights</a>
			{/if}
		</div>
		<div class="navbar-center hidden lg:flex"></div>
		<div class="navbar-end">
			{#if data.authed}
				<a class="btn btn-ghost" href="/logout" data-sveltekit-preload-data="off">Logout</a>
			{:else}
				<a class="btn btn-ghost" href="/login">Login</a>
			{/if}
		</div>
	</div>

	<div class="flex-1">
		{@render children()}
	</div>

	<footer class="footer sm:footer-horizontal footer-center bg-base-300 text-base-content p-4">
		<aside>
			<p>Copyright © {new Date().getFullYear()} - IXBRL VSME Reader</p>
		</aside>
	</footer>
</div>
