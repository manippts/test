{
    "name": "Quality Management",
    "version": "0.1",
    "description": """

        """,
    "author": "P P T S [India] Pvt.Ltd",
    "website": "http://www.pptssolutions.com",
    "depends": ['product','purchase','stock','sale_stock', 'account'],
    "category": "Warehouse",
    "init_xml": [],
    "demo_xml": [],
    "data":[
            'views/ir_sequence_data.xml',
            'views/quality_check_view.xml',
            'views/quality_product_view.xml',
            # 'views/product_view.xml',
            # 'views/calibration_view.xml',
            ],
            
    'installable': True,
    'auto_install': False,
    'application': True,
}
