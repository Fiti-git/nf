import pandas as pd
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html

from .models import ProductMaster, PendingProductApproval, ExcelUploadLog
from .forms import ExcelUploadForm
from core.models import Employee

@admin.register(ProductMaster)
class ProductMasterAdmin(admin.ModelAdmin):
    list_display = ('itcode', 'itdesc', 'outlet', 'sprice', 'cprice', 'barcode', 'asat_date')
    list_filter = ('outlet', 'asat_date')
    search_fields = ('itcode', 'itdesc', 'barcode')

@admin.register(ExcelUploadLog)
class ExcelUploadLogAdmin(admin.ModelAdmin):
    list_display = ('outlet', 'selected_date', 'uploaded_by', 'upload_timestamp')
    list_filter = ('outlet', 'selected_date')
    change_list_template = "admin/excel_upload_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-excel/', self.admin_site.admin_view(self.upload_excel), name='upload-excel'),
        ]
        return custom_urls + urls

    def upload_excel(self, request):
        if request.method == "POST":
            form = ExcelUploadForm(request.POST, request.FILES)
            
            # Re-apply queryset restriction on POST to prevent security bypass
            if not request.user.is_superuser:
                employee = getattr(request.user, 'employee_profile', None)
                if employee:
                    form.fields['outlet'].queryset = employee.outlets.all()

            if form.is_valid():
                outlet = form.cleaned_data['outlet']
                selected_date = form.cleaned_data['date']
                excel_file = request.FILES['excel_file']

                # 1. Save the Log Entry
                log = ExcelUploadLog.objects.create(
                    outlet=outlet,
                    selected_date=selected_date,
                    excel_file=excel_file,
                    uploaded_by=request.user
                )

                try:
                    # 2. Read Excel into Pandas
                    df = pd.read_excel(excel_file)
                    
                    # 3. Just store everything into the Pending/Temp table first
                    # We will do the comparison logic in the next step
                    pending_items = []
                    for _, row in df.iterrows():
                        pending_items.append(
                            PendingProductApproval(
                                outlet=outlet,
                                itcode=str(row.get('Itcode', '')),
                                itdesc=str(row.get('ItDesc', '')),
                                sprice=row.get('sprice', 0),
                                cprice=row.get('cprice', 0),
                                asat_date=row.get('asatDate', selected_date),
                                barcode=str(row.get('itembarcode', '')),
                                status='PENDING'
                            )
                        )
                    
                    # Bulk create for speed
                    PendingProductApproval.objects.bulk_create(pending_items)
                    
                    messages.success(request, f"Successfully uploaded {len(pending_items)} items to the temporary table.")
                    return redirect("admin:inventory_pendingproductapproval_changelist")

                except Exception as e:
                    messages.error(request, f"Error processing Excel: {str(e)}")
        else:
            form = ExcelUploadForm()
            # Restrict the dropdown if the user is not a superuser
            if not request.user.is_superuser:
                employee = getattr(request.user, 'employee_profile', None)
                if employee:
                    form.fields['outlet'].queryset = employee.outlets.all()
        
        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': "Upload Inventory Excel"
        }
        return render(request, "admin/excel_upload_form.html", context)

@admin.register(PendingProductApproval)
class PendingApprovalAdmin(admin.ModelAdmin):
    list_display = ('itcode', 'itdesc', 'outlet', 'sprice', 'barcode', 'status', 'asat_date')
    list_filter = ('outlet', 'status')
    list_editable = ('barcode',)
    search_fields = ('itcode', 'itdesc')
    actions = ['approve_and_move_to_master']

    @admin.action(description="Approve selected items and move to Master Table")
    def approve_and_move_to_master(self, request, queryset):
        count = 0
        for item in queryset:
            # Update or Create in ProductMaster
            ProductMaster.objects.update_or_create(
                outlet=item.outlet,
                itcode=item.itcode,
                defaults={
                    'itdesc': item.itdesc,
                    'sprice': item.sprice,
                    'cprice': item.cprice,
                    'asat_date': item.asat_date,
                    'barcode': item.barcode,
                }
            )
            item.status = 'APPROVED'
            item.save()
            count += 1
        
        self.message_user(request, f"Successfully moved {count} items to Product Master.")