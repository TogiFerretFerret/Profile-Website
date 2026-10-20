<?php
// riverxia.sh geocities skin tweaks for Roundcube (elastic): just loads geo.css on every page.
class geostyle extends rcube_plugin
{
    public $task = '.*';

    public function init()
    {
        $this->include_stylesheet('geo.css');
    }
}
