# Custom Buck2 helper rules for Profile-Website
# Pure Starlark rules providing hermetic build, check, preview, and test targets.

def _sh_run_impl(ctx: AnalysisContext) -> list[Provider]:
    runner = ctx.actions.declare_output(ctx.attrs.name + ".sh")
    ctx.actions.write(
        runner,
        "#!/usr/bin/env bash\nset -euo pipefail\n" + ctx.attrs.script + "\n",
        is_executable = True,
    )
    return [
        DefaultInfo(default_output = runner),
        RunInfo(args = cmd_args(runner)),
    ]

sh_run = rule(
    impl = _sh_run_impl,
    attrs = {
        "script": attrs.string(),
    },
)

def _gen_site_impl(ctx: AnalysisContext) -> list[Provider]:
    out = ctx.actions.declare_output(ctx.attrs.name, dir = True)
    # Action builds site into out directory
    ctx.actions.run(
        cmd_args([
            "python3",
            ctx.attrs.build_script,
            "--prod",
        ]),
        category = "build_site",
    )
    return [DefaultInfo(default_output = out)]

gen_site = rule(
    impl = _gen_site_impl,
    attrs = {
        "build_script": attrs.source(),
        "srcs": attrs.list(attrs.source(), default = []),
    },
)
