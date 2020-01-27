# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

'''

These settings are required in config.yaml for this to work:

plugins:
  PBCuraEngine:
    cura_engine: /home/pi/CuraEngine/build/CuraEngine
    default_profile: /home/pi/.octoprint/slicingProfiles/PBCuraEngine/Test_One.profile


Additionally, the limitation with slicing profiles can be avoided by entering the following:

slicing:
  defaultProfiles:
    PBCuraEngine: Test_One

'''

import logging
import logging.handlers
import subprocess
import os
import flask
import math

import octoprint.plugin
import octoprint.util
import octoprint.slicing
import octoprint.settings

from octoprint.util.paths import normalize as normalize_path
from octoprint.util import to_unicode
from copy import deepcopy


class PBCuraEnginePlugin(octoprint.plugin.SlicerPlugin,
                         octoprint.plugin.SettingsPlugin,
                         octoprint.plugin.TemplatePlugin,
                         octoprint.plugin.AssetPlugin,
                         octoprint.plugin.BlueprintPlugin,
                         octoprint.plugin.StartupPlugin):

    def __init__(self):
        self._cura_logger = logging.getLogger('octoprint.plugins.pbcura.engine')

    def initialize(self):
        existing_settings = self._settings.global_get(['plugins', 'PBCuraEngine'], asdict=True)
        if existing_settings==None:
            default_settings = self.get_settings_defaults()
            self._settings.set(['cura_engine'], default_settings.get('cura_engine', None))
            self._settings.set(['default_profile'], default_settings.get('default_profile', None))
            self._settings.set_boolean(['debug_logging'], default_settings.get('debug_logging', False))

    def _is_engine_configured(self, cura_engine=None):
        if cura_engine is None:
            cura_engine = normalize_path(self._settings.get(['cura_engine']))
        return cura_engine is not None and os.path.isfile(cura_engine) and os.access(cura_engine, os.X_OK)

    def _is_profile_available(self):
        return bool(self._slicing_manager.all_profiles('PBCuraEngine', require_configured=False))

    @octoprint.plugin.BlueprintPlugin.route('/import', methods=['POST'])
    def import_cura_profile(self):
        '''
        Using this for development right now to manually upload the slicing
        profiles
        '''
        self._logger.info('Calling the profile upload page')

        import flask
        import json

        upload_name = flask.request.values.get('file.name', None)
        upload_path = flask.request.values.get('file.path', None)

        file_handle = open(upload_path, 'r')
        self._logger.info('Maybe we have a file')

        # convert the file to JSON
        slicer_settings = json.load(file_handle)

        profile_name = slicer_settings.get('name')

        self._logger.info(slicer_settings)
        self._logger.info(self._slicing_manager.registered_slicers)

        # fixme: need to generate profile_name from the file path
        # (or the json parameter)

        from octoprint.server.api import valid_boolean_trues
        if 'name' in flask.request.values and profile_name==None:
            profile_name = flask.request.values['name']
        if 'displayName' in flask.request.values:
            profile_display_name = flask.request.values['displayName']
        if 'description' in flask.request.values:
            profile_description = flask.request.values['description']
        if 'allowOverwrite' in flask.request.values:
            profile_allow_overwrite = flask.request.values['allowOverwrite'] in valid_boolean_trues
        if 'default' in flask.request.values:
            profile_make_default = flask.request.values['default'] in valid_boolean_trues

        self._slicing_manager.save_profile('PBCuraEngine',
                                           profile_name,
                                           slicer_settings,
                                           overrides=None,
                                           allow_overwrite=True,
                                           display_name=None,
                                           description=None)
        # Fixme: this should redirect to root.
        result = dict(
            resource=flask.url_for('api.slicingGetSlicerProfile', slicer='PBCuraEngine', name=profile_name, _external=True),
            name=profile_name,
            displayName=profile_display_name,
            description=profile_description
        )
        r = flask.make_response(flask.jsonify(result), 201)
        r.headers['Location'] = result['resource']
        return r

    def is_slicer_configured(self):
        # fixme: actually do stuff here.
        # note: this gets called every time UI renders.
        # (so I'm putting a bunch of diagnostic printfs here)
        self._logger.info('Slicer configuration check')
        self._logger.info(self._slicing_manager.registered_slicers)
        self._logger.info('Profile List:')
        # fixme: this has stopped showing named profiles.
        self._logger.info(self._slicing_manager.all_profiles('PBCuraEngine'))
        return True

    def get_slicer_properties(self):
        return dict(type='PBCuraEngine',
                    name='Printrbot CuraEngine Slicer',
                    same_device=True,
                    progress_report=False,
                    source_file_types=['stl'],
                    destination_extensions=['gcode'])


    def get_slicer_default_profile(self):
        # if this isn't specified in config.yaml, override with bundled file
        pr_path = self._settings.get(['default_profile'])
        if pr_path==None:
            # fixme: maybe use a better name than Test_One.profile.
            pr_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'profiles', 'Test_One.profile')

        return self.get_slicer_profile(pr_path)

    def get_slicer_profile(self, path):
        # this is called to populate the list of slicer profiles
        # based on the .profile files located in:
        # ~/.octoprint/slicingProfiles/<slicerName>/

        # there's a function in types.py, get_slicer_profiles, that
        # handles this for OctoPrint.

        # This is going to open the file located in
        # ~/.octoprint/slicingProfiles/<slicerName>/profileName.profile

        self._logger.info('Getting slicer profile. Path:')
        self._logger.info(path)

        import json
        file_handle = open(path, 'r')
        slicer_settings = json.load(file_handle)


        display_name = None
        description = None
        slicer_name = self.get_slicer_properties()['type']
        profile_name = None

        # using Gina's convention to pass metadata
        if '_display_name' in slicer_settings:
            display_name = slicer_settings['_display_name']
            del slicer_settings['_display_name']
        if '_description' in slicer_settings:
            description = slicer_settings['_description']
            del slicer_settings['_description']

        # grab the profile name from the path
        # fixme: keep an eye if tempfile paths are provided here often.
        # (this may not work if using tmpfile)
        # fixme: walk this code. It might not be quite...right.
        p_path = os.path.splitext(path)
        profile_name = path[0]

        # Fixme:
        # I don't like the direct call to octoprint.slicing.SlicingProfile
        return octoprint.slicing.SlicingProfile(slicer_name,
                                                profile_name,
                                                slicer_settings,
                                                display_name,
                                                description)

    def save_slicer_profile(self, path, profile, allow_overwrite=True,
                            overrides=None):

        import json
        self._logger.info('We\'re saving a slicer profile')
        self._logger.info(path)
        self._logger.info(overrides)
        # This is called when do_slicer is invoked. OctoPrint writes the
        # SlicingProfile to a temp file with this mechanism.

        # fixme: ignores overrides. These should be blended with
        # the profile.
        # fixme: no belts or suspenders here. Add error checking.
        # overrides is a dict
        file_handle = open(path, 'w')
        json.dump(profile.data, file_handle, indent=4, sort_keys=True)
        file_handle.close()

    def on_after_startup(self):
        self._logger.info('PBCuraEngine Plugin is running')
        self._logger.info(self._identifier)
        self._logger.info('Slicer list:')
        self._logger.info(self._slicing_manager.registered_slicers)
        self._slicing_manager.initialize()

    def do_slice(self, model_path, printer_profile, machinecode_path=None,
                 profile_path=None, position=None, on_progress=None,
                 on_progress_args=None, on_progress_kwargs=None):

        self._logger.info('We\'re starting a slice. Buckle up.')

        self._logger.info('Here\'s the profile_path.')
        self._logger.info(profile_path)

        # This is covered in on_slice documentation
        if on_progress is not None:
            if on_progress_args is None:
                on_progress_args = ()
            if on_progress_kwargs is None:
                on_progress_kwargs = dict()
        # fixme: check if this is the best place for this.
        last_progress = 0

        self._logger.info('Model Path:')
        self._logger.info(model_path)

        # we don't expect to be given a machinecode_path, so infer
        # from the model_path

        self._logger.info('Just checking:')
        self._logger.info(machinecode_path)

        if not machinecode_path:
            self._logger.info('Working on machinecode path')
            m_path = os.path.splitext(model_path)
            self._logger.info(m_path)
            # Fixme! This line is crashing the slicer code
            # when initiating a slice from Printrhub
            # This probably never worked.
            machinecode_path = m_path[0] + '.gcode'
            self._logger.info('Did this work?')

        self._logger.info('Calculating machinecode_path:')
        self._logger.info(machinecode_path)

        # fixme: steps required are:
        # 4) add the abilty to cancel slicing in progress

        # We base the slicing on a settings.json (packaged with Cura UI)
        # and then sets 'quality-specific' overrides with the
        # octoPrint slicer settings.

        # Cura Executable from config.yaml:
        cura_path = self._settings.get(['cura_engine'])

        self._logger.info('Cura Path:')
        self._logger.info(cura_path)

        # This is the 'settings.json' file that curaEngine cmd line
        # wants (and is prefixed with -j). DO NOT confuse with
        # printer_profile which is stored in ~/.octoprint/slicingProfiles
        # and is a list of individual -s overrides.
        # Fixme: confirm that the default AND config-specified both work.
        settings_json_path = self._settings.get(['settings_json_path'])
        if not settings_json_path:
            settings_json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'profiles')
        # Now the profile.
        settings_json = self._settings.get(['settings_json'])
        if not settings_json:
            settings_json = 'fdmprinter.def.json'

        # Slicing Profile from system
        slice_vars = None
        if profile_path:
            slice_profile = self.get_slicer_profile(profile_path)
            slice_vars = slice_profile.data
            self._logger.info('Here are the slicing variables, recovered')
            self._logger.info(slice_vars)
        else:
            self._logger.info('we didn\'t get a profile path for do_slice')
            slice_profile = self.get_slicer_default_profile()
            slice_vars = slice_profile.data

        search_path_var = [
            os.path.join(settings_json_path,'definitions'),
            os.path.join(settings_json_path,'extruders'),
            os.path.join(settings_json_path,'quality'),
            os.path.join(settings_json_path,'variants')
        ]

        env = {
            'CURA_ENGINE_SEARCH_PATH':':'.join(search_path_var)
        }
        self._logger.info(env)
        import multiprocessing
        args = [
            cura_path,
            'slice',
            '-j',
            profile_path,
            '-v',
            '-p',
            '-m'+str(multiprocessing.cpu_count()),
            '-o',
            machinecode_path,
            '-l',
            model_path
        ]
        insert_index = args.index('-o')-1

        if isinstance(slice_vars,type({})):
            profile_metadata = slice_vars.get('metadata')
            if isinstance(profile_metadata,type({})):
                print_settings = profile_metadata.get('octoprint_settings')
                if isinstance(print_settings,type({})):
                    for key in sorted(print_settings):
                        args.insert(insert_index,key+'='+str(print_settings[key]))
                        args.insert(insert_index,'-s')

        my_result = ''

        self._logger.info(' '.join(args))

        import sarge
        p = sarge.run(args, async=True,
                      stdout=sarge.Capture(),
                      stderr=sarge.Capture(),
                      env=env)

        p.wait_events()

        layer = None
        percent = None
        analysis = None

        while p.returncode is None:
            line = p.stderr.readline(timeout=0.5)

            if not line:
                p.commands[0].poll()
                continue

            self._logger.info(line.strip())

            # measure progress
            if line[-2:-1] == '%':
                # Expecting format: Progress:export:235:240     0.988320%
                progress = float(line[-10:-6])
                # Fixme: This check may not be necesssary.
                if progress > last_progress:
                    on_progress_kwargs['_progress'] = progress
                    on_progress(*on_progress_args, **on_progress_kwargs)
                    last_progress = progress

            # filter out the lines used for the analysis dict.
            if 'Filament used:' in line:
                # Expecting format: Filament used: 1.234567m
                length = line.split(':')[1].strip()
                length = length[:-1] # chop off the m
                length = float(length) * 1000 # convert mm

                if analysis == None:
                    analysis = {}

                analysis['filament'] = {}
                analysis['filament']['tool0'] = {}
                analysis['filament']['tool0']['length'] = length
                # fixme: actually implement this
                analysis['filament']['tool0']['volume'] = 10

            if 'Print time:' in line:
                # Expecting format: 'Print time: 1234' (seconds)
                time = line.split(':')[1].strip()
                time = int(time)//60

                if analysis == None:
                    analysis = {}

                analysis['estimatedPrintTime'] = time

        p.close()
        # fixme: doesn't handle error/failure case.
        return analysis

    ##~~ TemplatePlugin API

    def get_template_vars(self):
        return dict(
            homepage='https://github.com/OctoPrint/OctoPrint-CuraEngineLegacy/'
        )

    ##~~ AssetPlugin API

    def get_assets(self):
        return {
            'js': ['js/PBCuraEngine.js'],
            'less': ['less/PBCuraEngine.less'],
            'css': ['css/PBCuraEngine.css']
        }

    ##~~ SettingsPlugin API

    def on_settings_save(self, data):
        old_engine = self._settings.get(['cura_engine'])
        old_debug_logging = self._settings.get_boolean(['debug_logging'])

        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        new_engine = self._settings.get(['cura_engine'])
        new_debug_logging = self._settings.get_boolean(['debug_logging'])

        if old_engine != new_engine and not self._is_engine_configured(new_engine):
            self._logger.info(u'Path to CuraEngine has not been configured or does not exist (currently set to %r), '
                              u'Cura will not be selectable for slicing' % new_engine)

        if old_debug_logging != new_debug_logging:
            if new_debug_logging:
                self._cura_logger.setLevel(logging.DEBUG)
            else:
                self._cura_logger.setLevel(logging.CRITICAL)

    def get_settings_defaults(self):
        return dict(
            cura_engine=None,
            default_profile=None,
            debug_logging=False
        )


    ##~~ StartupPlugin API

    def on_startup(self, host, port):
        # setup our custom logger
        from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
        cura_logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(postfix='pbcuraengine'), when='D', backupCount=3)
        cura_logging_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        cura_logging_handler.setLevel(logging.DEBUG)

        self._cura_logger.addHandler(cura_logging_handler)
        self._cura_logger.setLevel(logging.DEBUG if self._settings.get_boolean(['debug_logging']) else logging.CRITICAL)
        self._cura_logger.propagate = False

        engine = self._settings.get(['cura_engine'])
        if not self._is_engine_configured(cura_engine=engine):
            self._logger.info(u'Path to CuraEngine has not been configured or does not exist (currently set to %r), '
                              u'Cura will not be selectable for slicing' % engine)


def _sanitize_name(name):
    if name is None:
        return None

    if '/' in name or '\\' in name:
        raise ValueError(u'name must not contain / or \\')

    import string
    valid_chars = '-_.() {ascii}{digits}'.format(ascii=string.ascii_letters, digits=string.digits)
    sanitized_name = ''.join(c for c in name if c in valid_chars)
    sanitized_name = sanitized_name.replace(' ', '_')
    return sanitized_name.lower()


__plugin_name__ = 'PBCuraEngine'

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PBCuraEnginePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {

    }
