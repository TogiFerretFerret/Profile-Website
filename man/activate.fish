# Fish environment for Profile-Website manpages (venv-style)
# Usage: source man/activate.fish

set -l _man_dir (realpath (status dirname))

if set -q MANPATH
    set -gx _OLD_MANPATH "$MANPATH"
    set -gx MANPATH "$_man_dir:$MANPATH"
else
    set -e _OLD_MANPATH
    # Trailing colon preserves default system manpaths in man-db
    set -gx MANPATH "$_man_dir:"
end

function deactivate -d "Deactivate Profile-Website manpath environment"
    if set -q _OLD_MANPATH
        set -gx MANPATH "$_OLD_MANPATH"
        set -e _OLD_MANPATH
    else
        set -e MANPATH
    end
    functions -e deactivate
end
