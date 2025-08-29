"""
E-Learning Application Models Registry

This module serves as the central models registry for the E-Learning application.
It imports and exposes all models from the logical submodules (users, modules, final_exam)
to ensure they are properly registered with Django's ORM system.

The modular structure promotes separation of concerns while maintaining a unified
Django app namespace for the E-Learning functionality.

Architecture:
- users/: User management and authentication models
- modules/: Learning content and module management models
- final_exam/: Examination system and certification models

Author: DSP Development Team
Version: 1.0.0
"""

# Import all user-related models for registration with Django ORM
from .users.models import *

# Import all module-related models for registration with Django ORM
from .modules.models import *

# Import all final exam-related models for registration with Django ORM
from .final_exam.models import *
