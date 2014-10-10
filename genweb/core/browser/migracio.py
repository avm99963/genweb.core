from five import grok
from plone import api
from zope.component import getUtility

from Products.CMFPlone.interfaces import IPloneSiteRoot

from plone.registry.interfaces import IRegistry

import logging
import json
import requests
import os

LDAP_PASSWORD = os.environ.get('ldapbindpasswd', '')

logger = logging.getLogger(__name__)

PROPERTIES_MAP = {'titolespai_ca': 'html_title_ca',
                  'titolespai_es': 'html_title_es',
                  'titolespai_en': 'html_title_en',
                  'firmaunitat_ca': 'signatura_unitat_ca',
                  'firmaunitat_es': 'signatura_unitat_es',
                  'firmaunitat_en': 'signatura_unitat_en',
                  'contacteid': 'contacte_id',
                  'especific1': 'especific1',
                  'especific3': 'especific2',
                  'idestudiMaster': 'idestudi_master',
                  'boolmaps': 'contacte_no_upcmaps'}


class ExportGWConfig(grok.View):
    grok.context(IPloneSiteRoot)
    grok.name('export_gw_properties')
    grok.require('cmf.ManagePortal')

    def render(self):
        portal = api.portal.get()
        p_properties = portal.portal_properties
        properties_map = p_properties.genwebupc_properties.propertyMap()
        result = {}
        for gw_property in properties_map:
            result[gw_property['id']] = p_properties.genwebupc_properties.getProperty(gw_property['id'])

        # Translation flavour - GW4.2 settings
        legacy_skin = api.portal.get_tool('portal_skins').getDefaultSkin()
        result.update({'legacy_skin': legacy_skin})

        self.request.response.setHeader("Content-type", "application/json")
        return json.dumps(result)


class ImportGWConfig(grok.View):
    grok.context(IPloneSiteRoot)
    grok.name('import_gw_properties')
    grok.require('cmf.ManagePortal')

    def update(self):
        from genweb.controlpanel.interface import IGenwebControlPanelSettings

        self.registry = getUtility(IRegistry)
        self.gw_settings = self.registry.forInterface(IGenwebControlPanelSettings)

    def render(self):
        remote_server = 'http://127.0.0.1:9090'
        remote_path = '/ca1/ca1'
        remote_username = 'victor.fernandez'
        remote_token = 'uj5v4XrWMxGP25CN3pAE39mYCL7cwBMV'
        headers = {'X-Oauth-Username': remote_username,
                   'X-Oauth-Token': remote_token,
                   'X-Oauth-Scope': 'widgetcli',
                   }
        req = requests.get('{}{}/export_gw_properties'.format(remote_server, remote_path), headers=headers)
        properties = req.json()
        for prop in properties.keys():
            if prop in PROPERTIES_MAP.keys():
                self.map_gw_property(PROPERTIES_MAP[prop], properties[prop])

        if properties['tipusintranet'] == 'Visible':
            self.gw_settings.amaga_identificacio = False
        else:
            self.gw_settings.amaga_identificacio = True

        # N3
        if properties['legacy_skin'] == 'GenwebUPC_Neutre3':
            self.gw_settings.contacte_BBBDD_or_page = False
            self.gw_settings.contacte_al_peu = False
            self.gw_settings.directori_upc = False
            self.gw_settings.contrast_colors_bn = False
            self.gw_settings.treu_imatge_capsalera = False
            self.gw_settings.treu_menu_horitzontal = False
            self.gw_settings.treu_icones_xarxes_socials = False

        # N2
        elif properties['legacy_skin'] == 'GenwebUPC_Neutre2':
            self.gw_settings.contacte_BBBDD_or_page = False
            self.gw_settings.contacte_al_peu = False
            self.gw_settings.directori_upc = False
            self.gw_settings.contrast_colors_bn = False
            self.gw_settings.treu_imatge_capsalera = False
            self.gw_settings.treu_menu_horitzontal = True
            self.gw_settings.treu_icones_xarxes_socials = False

        # Unitat
        elif properties['legacy_skin'] == 'GenwebUPC_Unitat':
            self.gw_settings.contacte_BBBDD_or_page = False
            self.gw_settings.contacte_al_peu = False
            self.gw_settings.directori_upc = False
            self.gw_settings.contrast_colors_bn = False
            self.gw_settings.treu_imatge_capsalera = False
            self.gw_settings.treu_menu_horitzontal = False
            self.gw_settings.treu_icones_xarxes_socials = False

        # Master
        elif properties['legacy_skin'] == 'GenwebUPC_Master':
            self.gw_settings.contacte_BBBDD_or_page = False
            self.gw_settings.contacte_al_peu = False
            self.gw_settings.directori_upc = False
            self.gw_settings.contrast_colors_bn = False
            self.gw_settings.treu_imatge_capsalera = False
            self.gw_settings.treu_menu_horitzontal = True
            self.gw_settings.treu_icones_xarxes_socials = False

        else:
            logger.error("OJO! skin del site no reconegut! %s" % properties['legacy_skin'])
            return "OJO! skin del site no reconegut!" % properties['legacy_skin']

    def map_gw_property(self, prop, value):
        setattr(self.gw_settings, prop, value)
