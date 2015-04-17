from zope.interface import implementer
from zope.component import provideUtility
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer


@implementer(ICatalogFactory)
class UserPropertiesSoupCatalogFactory(object):
    """ The local user catalog (LUC) properties index factory. Almost all the
        properties have a field type "FullTextIndex" to allow wildcard queries
        on them. However, the FullTextIndex has a limitation its supported type
        of queries, so for certain operations is needed a FieldIndex for the
        username.

        :index id: FieldIndex - The username id for exact queries
        :index username: FullTextIndex - The username id for wildcard queries
        :index fullname: FullTextIndex - The user display name
        :index email: FullTextIndex - The user e-mail
        :index location: FullTextIndex - The user location
        :index ubicacio: FullTextIndex - The user ubicacio
        :index telefon: FullTextIndex - The user telephone
        :index twitter_username: FullTextIndex - The user Twitter username

        The properties attribute is used to know in advance which properties are
        listed as 'editable' or user accessible.
    """
    properties = ['username', 'fullname', 'email', 'location', 'ubicacio', 'telefon', 'twitter_username']

    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(idindexer)
        searchable_blob = NodeAttributeIndexer('searchable_text')
        catalog['searchable_text'] = CatalogTextIndex(searchable_blob)

        userindexer = NodeAttributeIndexer('username')
        catalog['username'] = CatalogTextIndex(userindexer)
        fullname = NodeAttributeIndexer('fullname')
        catalog['fullname'] = CatalogTextIndex(fullname)
        email = NodeAttributeIndexer('email')
        catalog['email'] = CatalogTextIndex(email)
        location = NodeAttributeIndexer('location')
        catalog['location'] = CatalogTextIndex(location)
        ubicacio = NodeAttributeIndexer('ubicacio')
        catalog['ubicacio'] = CatalogTextIndex(ubicacio)
        telefon = NodeAttributeIndexer('telefon')
        catalog['telefon'] = CatalogTextIndex(telefon)
        twitter_username = NodeAttributeIndexer('twitter_username')
        catalog['twitter_username'] = CatalogTextIndex(twitter_username)
        return catalog
provideUtility(UserPropertiesSoupCatalogFactory(), name="user_properties")


@implementer(ICatalogFactory)
class GroupsSoupCatalogFactory(object):
    """ The local user catalog (LUC) properties index factory. Almost all the
        properties have a field type "FullTextIndex" to allow wildcard queries
        on them. However, the FullTextIndex has a limitation its supported type
        of queries, so for certain operations is needed a FieldIndex for the
        username.

        :index id: FieldIndex - The group id for exact queries
        :index searchable_id: FullTextIndex - The group id used for wildcard
            queries
    """
    def __call__(self, context):
        catalog = Catalog()
        groupindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(groupindexer)
        idsearchableindexer = NodeAttributeIndexer('searchable_id')
        catalog['searchable_id'] = CatalogTextIndex(idsearchableindexer)
        return catalog
provideUtility(GroupsSoupCatalogFactory(), name="ldap_groups")
