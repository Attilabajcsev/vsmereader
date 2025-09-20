<script lang="ts">
    import { goto } from '$app/navigation';
    let { form } = $props();
</script>

<div class="hero bg-base-200 min-h-[95vh]">
	<div class="flex-col">
		<div class="mb-10 text-center lg:text-left">
			<h1 class="text-5xl font-bold">Login now!</h1>
			<p class="mt-2 text-sm opacity-70">Demo instance — for testing only</p>
		</div>
		<div class="card bg-base-100 w-full max-w-sm min-w-sm shrink-0 shadow-2xl">
			<div class="card-body">
                <form action="?/login" method="post">
					<fieldset class="fieldset">
						<label for="email" class="label">Email</label>
						<input
							required
							type="email"
							name="username"
							id="username"
							class="input"
							placeholder="Email address"
						/>
						<label for="password" class="label">Password</label>
						<input
							required
							type="password"
							class="input"
							name="password"
							id="password"
							placeholder="Password"
						/>
						<div><a class="link link-hover" href="/">Forgot password?</a></div>
                        <button type="submit" class="btn btn-neutral mt-4"> Login </button>
						<button type="button" class="btn" onclick={() => goto('/')}> Back </button>
					</fieldset>
				</form>
                {#if form?.message}
                    <div class="alert alert-error mt-3">{form.message}</div>
                {/if}
			</div>
		</div>
	</div>
</div>
