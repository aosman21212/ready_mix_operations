{
    'name': 'Ready Mix Operations',
    'version': '19.0.1.0.0',
    'summary': 'Complete Ready-Mix Concrete Operations Management',
    'description': """
        Manages the complete workflow for ready-mix concrete producers:
        - Plants & Silo Management
        - Mix Design / Concrete Products
        - Customer Job Sites & Rate Agreements
        - Delivery Scheduling & Dispatch Planning
        - Load Ticket Lifecycle
        - Quality Control (Fresh Tests, Cube/Cylinder Samples)
        - NCR / CAPA Non-Conformance Tracking
        - Cost Sheets & Invoicing
        - Moisture Logs & Certificates
        - Washout Records
        - Operations Dashboard & Reports
        - Customer Portal
    """,
    'category': 'Manufacturing',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'stock',
        'purchase',
        'account',
        'fleet',
        'portal',
        'mail',
    ],
    'data': [
        # Security
        'security/ready_mix_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ready_mix_sequence.xml',
        # Views
        'views/ready_mix_plant_views.xml',
        'views/ready_mix_silo_views.xml',
        'views/ready_mix_product_views.xml',
        'views/ready_mix_jobsite_views.xml',
        'views/ready_mix_rate_agreement_views.xml',
        'views/ready_mix_schedule_views.xml',
        'views/ready_mix_dispatch_views.xml',
        'views/ready_mix_load_views.xml',
        'views/ready_mix_qc_test_views.xml',
        'views/ready_mix_sample_views.xml',
        'views/ready_mix_ncr_views.xml',
        'views/ready_mix_cost_views.xml',
        'views/ready_mix_moisture_views.xml',
        'views/ready_mix_certificate_views.xml',
        'views/ready_mix_washout_views.xml',
        'views/ready_mix_dashboard_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizards/invoicing_wizard_views.xml',
        # Reports
        'report/ready_mix_load_report.xml',
        'report/ready_mix_load_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leap_ready_mix_operations/static/src/css/ready_mix.css',
        ],
    },
    'demo': [
        'demo/demo_partners.xml',
        'demo/demo_products.xml',
        'demo/demo_plant.xml',
        'demo/demo_mix_designs.xml',
        'demo/demo_commercial.xml',
        'demo/demo_operations.xml',
        'demo/demo_quality.xml',
        'demo/demo_compliance.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
