from django.urls import path

from package import views, banding_views, media_views

urlpatterns = [
    path('', views.collective_list, name='package_list'),
    path('inititatives/', views.initiative_list, name='initiative_list'),
    path('<int:package_id>/info/', views.package_info, name='package_info'),
    path('baskets/', views.view_baskets, name='basket_list'),
    path('baskets/<int:basket_id>/', views.view_basket, name='basket_detail'),
    path('baskets/<int:basket_id>/remove/<int:package_id>/',
         views.remove_from_basket,
         name='basket_remove_from_basket',
         ),
    path('baskets/<int:basket_id>/remove/meta/<int:meta_package_id>/',
         views.remove_from_basket,
         name='basket_remove_meta_from_basket',
         ),

    path('add_to_basket/package/<int:package_id>/', views.manage_basket,
         name='manage_basket_package'),
    path('add_to_basket/meta/<int:meta_package_id>/', views.manage_basket,
         name='manage_basket_meta_package'),

    path('checkout/start/<int:order_id>/',
         views.create_checkout_documents,
         name='start_checkout'),
    path('checkout/order/<int:order_id>/',
         views.order_form,
         name='order_form'),
    path('checkout/order/<int:order_id>/provisional/',
         views.order_provisional,
         name='order_provisional'),
    path('checkout/order/<int:order_id>/complete/',
         views.order_complete,
         name='order_complete'),
    path('checkout/order/<int:order_id>/download_order/',
         views.new_order_complete,
         name='new_order_complete',
         ),
    path('order/<int:order_id>/complete/',
         views.download_order_document,
         name='download_order_document',
         ),


    path('approval/', views.package_approval, name='package_approval'),
    path('setup/banding_types/list/', banding_views.banding_type_list,
         name='package_banding_type_list'),
    path('setup/banding_types/create/', banding_views.banding_type_create,
         name='package_banding_type_create'),
    path('setup/banding_types/<int:banding_type_id>/vocabs/',
         banding_views.banding_type_vocabs, name='package_banding_type_vocabs'),
  
    path('setup/form_elements/', views.form_elements_setup,
         name='form_element_setup'),
    path('setup/form_elements/order/', views.form_elements_order,
         name='form_element_order'),
    path('setup/form_elements/create/', views.form_element_create,
         name='form_element_create'),
    path('setup/form_elements/<int:form_element_id>/edit/',
         views.form_element_create,
         name='form_element_edit'),
    path('setup/form_elements/<int:form_element_id>/delete/',
         views.form_element_delete,
         name='form_element_delete'),

    path('signups/',
         views.list_signups,
         name='list_signups'),
    path('<int:package_id>/initiative/<int:initiative_id>/signups/'
         '<int:signup_id>/process/',
         views.process_signup,
         name='process_signup'),

    path('<int:package_id>/initiative/<int:initiative_id>/data/',
         views.package_data,
         name='package_data'),
    path('<int:package_id>/initiative/<int:initiative_id>/data/'
         'form_elements/<int:form_element_id>/delete/',
         views.form_element_package_delete,
         name='form_element_package_delete'),

    path('<int:package_id>/initiative/<int:initiative_id>/standards/',
         views.package_standards, name='package_standards'),
    path('<int:package_id>/initiative/<int:initiative_id>/standards/'
         '<int:standard_id>/attest/',
         views.package_standards_attest, name='package_standards_attest'),
    path('<int:package_id>/initiative/<int:initiative_id>/standards/'
         '<int:standard_id>/attest/delete/',
         views.package_standards_attest_delete,
         name='package_standards_attest_delete'),
    path('<int:package_id>/initiative/<int:initiative_id>/contacts/',
         views.package_contacts, name='package_contacts'),

    path('<int:package_id>/initiative/<int:initiative_id>/access_control/',
         views.package_access_control, name='package_access_control'),

    path('signup/<int:signup_id>/initiative/<int:initiative_id>/'
         'change_access/<str:access_type>/',
         views.package_access_control_change,
         name='package_access_control_change'),

    path('<int:package_id>/initiative/<int:initiative_id>/delete/',
         views.delete_package,
         name='delete_package'),

    path('<int:package_id>/initiative/<int:initiative_id>/banding/'
         '<int:banding_id>/delete/',
         views.delete_package_banding,
         name='delete_package_banding'),

    path('<int:package_id>/initiative/<int:initiative_id>/banding/'
         '<int:banding_id>/currency/<int:banding_currency_id>/delete/',
         views.delete_package_banding_currency,
         name='delete_package_banding_currency'),

    path('<int:package_id>/initiative/<int:initiative_id>/banding/'
         '<int:banding_id>/currencies/',
         views.manage_package_banding_currencies,
         name='manage_package_banding_currencies'),

    path('<int:package_id>/initiative/<int:initiative_id>/banding/'
         '<int:banding_id>/currencies/<int:currency_id>/prices/',
         views.manage_package_banding_currencies_prices,
         name='manage_package_banding_currencies_prices'),

    path('<int:package_id>/initiative/<int:initiative_id>/bandings/',
         views.manage_package_bandings,
         name='package_bandings'),

    path('<int:package_id>/initiative/<int:initiative_id>/banding/'
         '<int:banding_id>/redirect',
         views.edit_redirect_for_banding,
         name='edit_redirect_for_banding'),


    path('<int:package_id>/initiative/<int:initiative_id>/list_documents/',
         views.list_documents, name='list_documents'),
    path('<int:package_id>/initiative/<int:initiative_id>/add_document/',
         views.add_document, name='add_document'),
    path('<int:package_id>/initiative/<int:initiative_id>/revise/<int:document_id>/',
         views.upload_new_document, name='upload_new_document'),
    path('<int:package_id>/initiative/<int:initiative_id>/revise/<int:document_id>/revert/',
         views.revert_document_version, name='revert_document_version'),
    path('<int:package_id>/initiative/<int:initiative_id>/'
         'view_document/<int:document_id>',
         views.view_document, name='view_document'),
    path('<int:package_id>/initiative/<int:initiative_id>/'
         'document/<int:document_id>/delete/',
         views.delete_document, name='delete_document'),

    path('price_debugger/',
         views.price_debugger, name='price_debugger'),


    path('<int:package_id>/initiative/<int:initiative_id>/media_files/',
         media_views.list_media_files, name='media_files'),
    path('<int:package_id>/initiative/<int:initiative_id>/media_files/<int:file_id>/',
         media_views.download_media_file, name='download_media_file'),
]
