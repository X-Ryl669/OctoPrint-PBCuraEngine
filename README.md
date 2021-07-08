# OctoPrint-PBCuraEngine

PBCuraEngine is a plugin that adds the 'latest' CuraEngine slicer to
OctoPrint running on a Raspberry Pi.

We use the "PB" prefix because Cura is a pretty overloaded term, but
to be super-clear, this plugin uses ["vanilla" CuraEngine](https://github.com/Ultimaker/CuraEngine) with no modifications/enhancements.

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

      https://github.com/X-Ryl669/OctoPrint-PBCuraEngine/archive/master.zip

To use this plugin, you must have [CuraEngine](https://github.com/Ultimaker/CuraEngine/blob/master/README.md)
and its dependencies installed on your system. This plugin was
originally integrated with the version 3.x CuraEngine code and has since been tested working on 4.9.

There is an install script in the scripts directory of this repository to install CuraEngine.
This has been tested to work with 4.9 but should work with any version of CuraEngine.

To use the script, run `./install_curaengine.sh 4.9`. The script will ask for your account password multiple time using sudo.
Once the install script has finished, you'll need to run `./get_cura_profiles.sh $PLUGIN_DIR 4.9` with `$PLUGIN_DIR`
being the location octoprint has installed this plugin to,
for example on an octopi, this is `/home/pi/Octoprint/venv/lib/python3.7/site-packages/octoprint_PBCuraEngine`.
You can get the install location by looking in ocotprint's settings under the
plugin manager section there is "Using pip of <blah>", expand that and there is the install directory location.
Simply add `/octoprint_PBCuraEngine` to this directory location to get `$PLUGIN_DIR`.
You can change `4.9` used previously if you wish to use another version or for upgrades to CuraEngine.

For updating CuraEngine, all you should need to do is run `./install_curaengine.sh $CURAENGINE_VERSION` as root, where `$CURAENGINE_VERSION` is the git branch of [CuraEngine](https://github.com/Ultimaker/CuraEngine).

## Configuration

All configuration is done in the plugin menu provided in the web UI now.

## Slicer Settings

Slicer settings can be changed before slicing by having an additional JSON key under the `"metadata"` key.
The additional key under `"metadata"` is `"octoprint_settings"`, anything under here is used as a way for at slicing time overrides for the slicer.
The only issue with this that potientially certain options cannot be overriden because overrides don't merge
into the entire profile but only into the `"octoprint_settings"`.

For how to set up a slicing profile, see my exaple profile for my Creality Ender 3 Pro in the root of this repository under `example_profile`.

### Cura Settings.json

CuraEngine recently (in terms of versions) changed how profiles work.
My example printer profile is a great example of how this works and reading through it while reading this is highly recommended.
Basically its an inheritance system now, so for a custom profile all you need to do is
inherit from your own printer's existing profile (if one exists) then you can do changes in your profile.
So in my example profile, I set my extruder values since that isn't inherited and set my custom start and end gcode.
I set all my other options in the override JSON key because of the way my current not released patches to the
[slicer plugin](https://github.com/kennethjiang/OctoPrint-Slicer) work, which allows me to edit anything under the override JSON key.


## TODO:
- Clean up the plugin, its still rather messy.
- I may want to rename the plugin from its original name since its not exactly as it was or with the same intentions.
- Release my changes for [slicer plugin](https://github.com/kennethjiang/OctoPrint-Slicer) as a PR since they make using this plugin a breeze.

