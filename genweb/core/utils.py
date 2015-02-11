import json
import urllib2
import requests
from five import grok
from plone import api
from AccessControl import getSecurityManager
# from zope.interface import Interface
from zope.component import getMultiAdapter, queryUtility
from zope.i18nmessageid import MessageFactory
from zope.component.hooks import getSite
from zope.component import getUtility

from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from plone.app.multilingual.interfaces import ITranslationManager

from Products.CMFCore.utils import getToolByName
# from Products.CMFPlone import PloneMessageFactory as _
from Products.Five.browser import BrowserView
from Products.ATContentTypes.interface.folder import IATFolder
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from souper.interfaces import ICatalogFactory
from repoze.catalog.query import Eq
from souper.soup import get_soup
from souper.soup import Record
from zope.interface import implementer
from zope.component import provideUtility
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from souper.soup import NodeAttributeIndexer
from plone.uuid.interfaces import IMutableUUID

from genweb.controlpanel.interface import IGenwebControlPanelSettings

import logging

logger = logging.getLogger(__name__)

PLMF = MessageFactory('plonelocales')


def genweb_config():
    """ Funcio que retorna les configuracions del controlpanel """
    registry = queryUtility(IRegistry)
    return registry.forInterface(IGenwebControlPanelSettings)


def havePermissionAtRoot():
    """Funcio que retorna si es Editor a l'arrel"""
    proot = portal()
    pm = getToolByName(proot, 'portal_membership')
    sm = getSecurityManager()
    user = pm.getAuthenticatedMember()

    return sm.checkPermission('Modify portal content', proot) or \
        ('Manager' in user.getRoles()) or \
        ('Site Administrator' in user.getRoles())
    # WebMaster used to have permission here, but not anymore since uLearn
    # makes use of it
    # ('WebMaster' in user.getRoles()) or \


def portal_url():
    """Get the Plone portal URL out of thin air without importing fancy
       interfaces and doing multi adapter lookups.
    """
    return portal().absolute_url()


def portal():
    """Get the Plone portal object out of thin air without importing fancy
       interfaces and doing multi adapter lookups.
    """
    return getSite()


def pref_lang():
    """ Extracts the current language for the current user
    """
    lt = getToolByName(portal(), 'portal_languages')
    return lt.getPreferredLanguage()


def link_translations(items):
    """
        Links the translations with the declared items with the form:
        [(obj1, lang1), (obj2, lang2), ...] assuming that the first element
        is the 'canonical' (in PAM there is no such thing).
    """
    # Grab the first item object and get its canonical handler
    canonical = ITranslationManager(items[0][0])

    for obj, language in items:
        if not canonical.has_translation(language):
            canonical.register_translation(language, obj)


def _contact_ws_cachekey(method, self, unitat):
    """Cache by the unitat value"""
    return (unitat)


def get_safe_member_by_id(username):
    """Gets user info from the repoze.catalog based user properties catalog.
       This is a safe implementation for getMemberById portal_membership to
       avoid useless searches to the LDAP server. It gets only exact matches (as
       the original does) and returns a dict. It DOES NOT return a Member
       object.
    """
    portal = api.portal.get()
    soup = get_soup('user_properties', portal)
    user_properties_utility = getUtility(ICatalogFactory, name='user_properties')
    indexed_attrs = user_properties_utility(portal).keys()
    properties = None
    records = [r for r in soup.query(Eq('username', username))]
    if records:
        properties = {}
        for attr in indexed_attrs:
            if records[0].attrs.get(attr, False):
                properties[attr] = records[0].attrs[attr]
    return properties


class genwebUtils(BrowserView):
    """ Convenience methods placeholder genweb.utils view. """

    def portal(self):
        return api.portal.get()

    def havePermissionAtRoot(self):
        """Funcio que retorna si es Editor a l'arrel"""
        pm = getToolByName(self, 'portal_membership')
        proot = portal()
        sm = getSecurityManager()
        user = pm.getAuthenticatedMember()

        return sm.checkPermission('Modify portal content', proot) or \
            ('WebMaster' in user.getRoles()) or \
            ('Site Administrator' in user.getRoles())

    def pref_lang(self):
        """ Extracts the current language for the current user
        """
        lt = api.portal.get_tool('portal_languages')
        return lt.getPreferredLanguage()

    # def getDadesUnitat(self):
    #     """ Retorna les dades proporcionades pel WebService del SCP """
    #     unitat = genweb_config().contacte_id
    #     if unitat:
    #         dades = self._queryInfoUnitatWS(unitat)
    #         if dades.has_key('error'):
    #             return False
    #         else:
    #             return dades
    #     else:
    #         return False

    @ram.cache(_contact_ws_cachekey)
    def _queryInfoUnitatWS(self, unitat):
        try:
            r = requests.get('https://bus-soa.upc.edu/SCP/InfoUnitatv1?id=%s' % unitat, timeout=10)
            return r.json()
        except:
            return {}

    def getDadesUnitat(self):
        """ Retorna les dades proporcionades pel WebService del SCP """
        unitat = genweb_config().contacte_id
        if unitat:
            dades = self._queryInfoUnitatWS(unitat)
            if 'error' in dades:
                return False
            else:
                return dades
        else:
            return False

    def getDadesContact(self):
        """ Retorna les dades proporcionades pel WebService del SCP
            per al contacte
        """
        unitat = genweb_config().contacte_id
        if unitat:
            dades = self.getDadesUnitat()
            if 'error' in dades:
                return False
            else:
                idioma = self.context.Language()
                dict_contact = {
                    "ca": {
                        "adreca_sencera": dades.get('campus_ca', '') + ', ' + dades.get('edifici_ca') + '. ' + dades.get('adreca') + ' ' + dades.get('codi_postal') + " " + dades.get('localitat'),
                        "nom": dades.get('nom_ca', ''),
                        "telefon": dades.get('telefon', ''),
                        "fax": dades.get('fax', ''),
                        "email": dades.get('email', ''),
                        "id_scp": dades.get('id', ''),
                        "codi_upc": dades.get('codi_upc', ''),
                    },
                    "es": {
                        "adreca_sencera": dades.get('campus_es', '') + ', ' + dades.get('edifici_es') + '. ' + dades.get('adreca') + ' ' + dades.get('codi_postal') + " " + dades.get('localitat'),
                        "nom": dades.get('nom_es', ''),
                        "telefon": dades.get('telefon', ''),
                        "fax": dades.get('fax', ''),
                        "email": dades.get('email', ''),
                        "id_scp": dades.get('id', ''),
                        "codi_upc": dades.get('codi_upc', ''),
                    },
                    "en": {
                        "adreca_sencera": dades.get('campus_en', '') + ', ' + dades.get('adreca') + ' ' + dades.get('codi_postal') + " " + dades.get('localitat'),
                        "nom": dades.get('nom_en', ''),
                        "telefon": dades.get('telefon', ''),
                        "fax": dades.get('fax', ''),
                        "email": dades.get('email', ''),
                        "id_scp": dades.get('id', ''),
                        "codi_upc": dades.get('codi_upc', ''),
                    }
                }
                return dict_contact[idioma]
        else:
            return False

    def getContentClass(self, view=None):
        plone_view = getMultiAdapter((self.context, self.request), name=u'plone')
        sl = plone_view.have_portlets('plone.leftcolumn', view=view)
        sr = plone_view.have_portlets('plone.rightcolumn', view=view)

        if not sl and not sr:
            return 'span12'
        if (sl and not sr) or (not sl and sr):
            return 'span9'
        if sl and sr:
            return 'span6'

    def getProgressBarName(self, number, view=None):
        if number == 1:
            return "progress progress-success"
        elif number == 2:
            return "progress progress-primary"
        elif number == 3:
            return "progress progress-warning"
        elif number == 4:
            return "progress progress-danger"
        return "progress progress-info"

    def get_proper_menu_list_class(self, subMenuItem):
        """ For use only in the menus to calculate the correct class value of
            some f*cking elements
        """
        if subMenuItem['extra']['id'] == 'plone-contentmenu-settings':
            return 'actionSeparator'
        if subMenuItem['extra']['id'] != 'contextSetDefaultPage':
            return subMenuItem['extra']['separator']
        else:
            return None

    def get_state_label_class_mapping(self):
        return {
            'visible': 'label-success',
            'esborrany': 'label-success',
            'published': 'label-primary',
            'intranet': 'label-intranet',
            'private': 'label-important',
            'pending': 'label-warning',
            'restricted-to-managers': 'label-inverse',
        }

    def pref_lang_native(self):
        """ Extracts the current language for the current user in native
        """
        lt = getToolByName(portal(), 'portal_languages')
        return lt.getAvailableLanguages()[lt.getPreferredLanguage()]['native']

    def get_published_languages(self):
        return genweb_config().idiomes_publicats

    def is_ldap_upc_site(self):
        acl_users = api.portal.get_tool(name='acl_users')
        if 'ldapUPC' in acl_users:
            return True
        else:
            return False

    def redirect_to_root_always_lang_selector(self):
        return genweb_config().languages_link_to_root

    def premsa_url(self):
        """Funcio que extreu la URL de Sala de Premsa
        """
        idioma = pref_lang()

        if idioma == 'zh':
            url = 'http://www.upc.edu/saladepremsa/?set_language=en'
        else:
            url = 'http://www.upc.edu/saladepremsa/?set_language=' + idioma
        return url


@implementer(ICatalogFactory)
class UserPropertiesSoupCatalogFactory(object):
    def __call__(self, context):
        catalog = Catalog()
        path = NodeAttributeIndexer('path')
        catalog['path'] = CatalogFieldIndex(path)
        uuid = NodeAttributeIndexer('uuid')
        catalog['uuid'] = CatalogFieldIndex(uuid)
        return catalog
provideUtility(UserPropertiesSoupCatalogFactory(), name="uuid_preserver")


class preserveUUIDs(grok.View):
    grok.context(IPloneSiteRoot)

    def render(self):
        portal = api.portal.get()
        soup = get_soup('uuid_preserver', portal)
        pc = api.portal.get_tool('portal_catalog')
        results = pc.searchResults()

        for result in results:
            record = Record()
            record.attrs['uuid'] = result.UID
            record.attrs['path'] = result.getPath()
            soup.add(record)
            logger.warning('Preserving {}: {}'.format(result.getPath(), result.UID))


class rebuildUUIDs(grok.View):
    grok.context(IPloneSiteRoot)

    def render(self):
        portal = api.portal.get()
        soup = get_soup('uuid_preserver', portal)
        pc = api.portal.get_tool('portal_catalog')
        results = pc.searchResults()

        for result in results:
            obj = [r for r in soup.query(Eq('path', result.getPath()))]
            if obj:
                try:
                    realobj = result.getObject()
                    IMutableUUID(realobj).set(str(obj[0].attrs['uuid']))
                    realobj.reindexObject(idxs=['UID'])
                    logger.warning('Set UUID per {}'.format(result.getPath()))
                except:
                    logger.warning('Can\'t set UUID for {}'.format(result.getPath()))


# Per deprecar (not wired):
class utilitats(BrowserView):

    _dadesUnitat = None

    def havePermissionAtRoot(self):
        """Funcio que retorna si es Editor a l'arrel"""
        pm = getToolByName(self, 'portal_membership')
        sm = getSecurityManager()
        user = pm.getAuthenticatedMember()

        return sm.checkPermission('Modify portal content', portal()) or ('WebMaster' in user.getRoles())

    def _getDadesUnitat(self):
        """ Retorna les dades proporcionades pel WebService del SCP
        """
        id = self.getGWConfig().contacteid
        if id:
            if self._dadesUnitat is None:
                try:
                    url = urllib2.urlopen('https://bus-soa.upc.edu/SCP/InfoUnitatv1?id=' + id, timeout=10)
                    respuesta = url.read()
                    self._dadesUnitat = json.loads(respuesta)
                except:
                    pass
        return self._dadesUnitat

    def getTitol(self):
        lt = getToolByName(self, 'portal_languages')
        lang = lt.getPreferredLanguage()
        gw_config = self.getGWConfig()
        titol = getattr(gw_config, 'titolespai_%s' % lang)
        return titol

    def getGWProperty(self, gwproperty):
        """Retorna de manera segura una propietat del GW"""
        property_value = getattr(self.getGWConfig(), gwproperty, '')
        if property_value is None:
            property_value = ''
        return property_value

    def llistaEstats(self):
        """Retorna una llista dels estats dels workflows indicats
        """
        wtool = getToolByName(self, 'portal_workflow')
        workflows = ['genweb_simple', 'genweb_review']
        estats = []
        for w in workflows:
            estats = estats + [s[0] for s in wtool.getWorkflowById(w).states.items()]

        return [w for w in wtool.listWFStatesByTitle() if w[0] in estats]

    def llistaContents(self):
        """Retorna tots els tipus de contingut, exclosos els de la llista types_to_exclude"""
        types_to_exclude = ['Banner', 'BannerContainer', 'CollageAlias', 'CollageColumn', 'CollageRow', 'Favorite', 'Large Plone Folder', 'Logos_Container', 'Logos_Footer', 'PoiPscTracker', 'SubSurvey', 'SurveyMatrix', 'SurveyMatrixQuestion', 'SurveySelectQuestion', 'SurveyTextQuestion', ]
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        ptypes = portal_state.friendly_types()
        for typeEx in types_to_exclude:
            if typeEx in ptypes:
                ptypes.remove(typeEx)

        return ptypes

    def portal_url(self):
        """ Funcion a que retorna el path"""
        context_state = getMultiAdapter((self.context, self.request),
                                        name=u'plone_context_state')
        return context_state.current_base_url()

    def dia_semana(self, day):
        """ Funcion a la que le pasas el dia y te lo devuelve en modo texto"""
        _ts = getToolByName(self, 'translation_service')
        dia = day + 1
        if dia == 7:
            dia = 0
        return PLMF(_ts. day_msgid(dia), default=_ts.weekday_english(dia, format='a'))

    def mes(self, month):
        """ Funcion a la que le pasas el mes y te lo devuelve en modo texto
        """
        _ts = getToolByName(self, 'translation_service')
        return PLMF(_ts.month_msgid(month), default=_ts.month_english(month, format='a'))

    def pref_lang(self):
        """Funcio que extreu idioma actiu
        """
        lt = getToolByName(self, 'portal_languages')
        return lt.getPreferredLanguage()

    def getGWConfig(self):
        """ Funcio que retorna les configuracions del controlpanel
        """
        ptool = getToolByName(self.context, 'portal_properties')
        try:
            gwconfig = ptool.genwebupc_properties
        except:
            gwconfig = None

        return gwconfig

    def isFolder(self):
        """ Funcio que retorna si es carpeta per tal de mostrar o no el last modified
        """
        if IATFolder.providedBy(self.context) or IPloneSiteRoot.providedBy(self.context):
            return True

    def remapList2Dic(self, dictkeys, results):
        _dictResult = {}
        _dictKeys = dictkeys
        _results = results
        c = 0
        for ii in _dictKeys:
            _dictResult[ii] = _results[c]
            c = c + 1
        return _dictResult

    def recodifica(self, str):
        return str.decode('iso-8859-1').encode('utf-8')

    def getDirectori(self):
        ue = self._dadesUnitat['codi_upc']
        return "http://directori.upc.edu/directori/dadesUE.jsp?id=" + ue

    def getNomCentre(self):
        """ Retorna el nom del centre segons l'idioma
        """
        lang = self.pref_lang()
        nom_centre = self._dadesUnitat['nom_' + lang]
        return nom_centre

    def getEdifici(self):
        """Retorna edifici en l'idioma del portal
        """
        lang = self.pref_lang()
        edifici = self._dadesUnitat['edifici_' + lang]
        return edifici

    def getCampus(self):
        """Retorna edifici en l'idioma del portal
        """
        lang = self.pref_lang()
        campus = self._dadesUnitat['campus_' + lang]
        return campus

    def fields2Dic(self, dc, de, di):
        tmp = (dc, de, di)
        dictKeys = ('doc_ca', 'doc_es', 'doc_en',)
        return self.remapList2Dic(dictKeys, tmp)

    def test(self, value, trueVal, falseVal):
        """
            helper method, mainly for setting html attributes.
        """
        if value:
            return trueVal
        else:
            return falseVal

    def getSectionFromURL(self):
        context = self.context
        # portal_url=getToolByName(context, 'portal_url')
        tools = getMultiAdapter((self.context, self.request), name=u'plone_tools')

        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        contentPath = tools.url().getRelativeContentPath(context)
        if not contentPath:
            return ''
        else:
            return portal_state.portal()[contentPath[0]].Title().replace('&nbsp;', '')

    def getFlavour(self):
        portal_skins = getToolByName(self.context, 'portal_skins')
        return portal_skins.getDefaultSkin()

    def premsa_PDIPAS_url(self):
        """Funcio que extreu idioma actiu
        """
        lt = getToolByName(self, 'portal_languages')
        idioma = lt.getPreferredLanguage()
        if idioma == 'zh':
            url = 'http://www.upc.edu/saladepremsa/pdi-pas/?set_language=en'
        else:
            url = 'http://www.upc.edu/saladepremsa/pdi-pas/?set_language=' + idioma
        return url
