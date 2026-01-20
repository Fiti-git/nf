import pandas as pd
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

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

            # Restrict outlet queryset for non-superusers
            if not request.user.is_superuser:
                employee = getattr(request.user, 'employee_profile', None)
                if employee:
                    form.fields['outlet'].queryset = employee.outlets.all()

            if form.is_valid():
                outlet = form.cleaned_data['outlet']
                selected_date = form.cleaned_data['date']
                excel_file = request.FILES['excel_file']

                # Save upload log entry
                log = ExcelUploadLog.objects.create(
                    outlet=outlet,
                    selected_date=selected_date,
                    excel_file=excel_file,
                    uploaded_by=request.user
                )

                try:
                    # Step 1: Load raw Excel without headers, detect header row
                    df_raw = pd.read_excel(excel_file, header=None, engine='xlrd')

                    header_row = None
                    for i in range(15):
                        row_text = df_raw.iloc[i].astype(str).str.lower().to_string()
                        if 'item' in row_text:
                            header_row = i
                            break

                    if header_row is None:
                        raise ValueError("Could not detect header row containing 'item' keyword.")

                    # Reload with proper header row
                    excel_file.seek(0)  # Reset file pointer
                    df = pd.read_excel(excel_file, header=header_row, engine='xlrd')

                    # Step 2: Clean DataFrame
                    df = df.dropna(how='all').dropna(axis=1, how='all')
                    df.columns = df.columns.str.strip()

                    # Rename duplicate columns if any
                    cols = df.columns.tolist()
                    for idx, col in enumerate(cols):
                        if cols.count(col) > 1:
                            first_idx = cols.index(col)
                            if idx != first_idx:
                                cols[idx] = f"{col}_{idx}"
                    df.columns = cols

                    # Rename Unnamed: 2 to ItDesc
                    if 'Unnamed: 2' in df.columns:
                        df = df.rename(columns={'Unnamed: 2': 'ItDesc'})

                    # Drop unwanted columns if they exist
                    for col in ['Unnamed: 4', 'COST_1', 'SELLING VALUE']:
                        if col in df.columns:
                            df = df.drop(columns=[col])

                    # Filter rows where 'ITEM' is valid product code
                    df = df[df['ITEM'].notna()]
                    df = df[df['ITEM'].str.match(r'^[A-Za-z]+\d+', na=False)]
                    df = df[~df['ITEM'].str.contains('copyright', case=False, na=False)]

                    # Convert numeric columns to numbers, adjust based on your columns
                    numeric_cols = ['TTL LTR', 'COST', 'SELLING', 'SIH']
                    existing_numeric_cols = [col for col in numeric_cols if col in df.columns]
                    for col in existing_numeric_cols:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                    # Filter rows with valid numeric SIH and COST >= 0
                    if 'SIH' in df.columns and 'COST' in df.columns:
                        df = df[(df['SIH'] >= 0) & (df['COST'] >= 0)]

                    df = df.reset_index(drop=True)

                    # Step 3: Prepare PendingProductApproval entries
                    pending_items = []
                    for _, row in df.iterrows():
                        pending_items.append(
                            PendingProductApproval(
                                outlet=outlet,
                                itcode=str(row.get('ITEM', '')).strip(),
                                itdesc=str(row.get('ItDesc', '')).strip() if 'ItDesc' in df.columns else '',
                                sprice=row.get('SELLING', 0) if 'SELLING' in df.columns else 0,
                                cprice=row.get('COST', 0) if 'COST' in df.columns else 0,
                                asat_date=selected_date,
                                barcode=str(row.get('barcode', '')).strip() if 'barcode' in df.columns else '',
                                status='PENDING'
                            )
                        )

                    # Bulk create entries
                    PendingProductApproval.objects.bulk_create(pending_items)

                    messages.success(request, f"Successfully uploaded {len(pending_items)} items to the temporary table.")
                    return redirect("admin:inventory_pendingproductapproval_changelist")

                except Exception as e:
                    messages.error(request, f"Error processing Excel: {str(e)}")

        else:
            form = ExcelUploadForm()
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
