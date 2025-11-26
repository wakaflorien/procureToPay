import React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Proforma Invoice Form Schema
const proformaSchema = z.object({
  vendor: z.string().min(1, 'Vendor name is required'),
  amount: z.number().min(0.01, 'Amount must be greater than 0'),
  items: z.array(
    z.object({
      name: z.string().min(1, 'Item name is required'),
      quantity: z.number().min(1, 'Quantity must be at least 1'),
      unit_price: z.number().min(0.01, 'Unit price must be greater than 0'),
      total: z.number().min(0.01, 'Total must be greater than 0'),
    })
  ).min(1, 'At least one item is required'),
  terms: z.string().optional(),
});

export type ProformaFormData = z.infer<typeof proformaSchema>;

interface ProformaInvoiceFormProps {
  initialData?: Partial<ProformaFormData>;
  onSubmit: (data: ProformaFormData) => void | Promise<void>;
  onCancel?: () => void;
  isLoading?: boolean;
}

const ProformaInvoiceForm: React.FC<ProformaInvoiceFormProps> = ({ 
  initialData, 
  onSubmit, 
  onCancel, 
  isLoading = false 
}) => {
  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ProformaFormData>({
    resolver: zodResolver(proformaSchema),
    defaultValues: initialData || {
      vendor: '',
      amount: 0,
      items: [{ name: '', quantity: 1, unit_price: 0, total: 0 }],
      terms: '',
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'items',
  });

  // Watch items to calculate totals
  const watchedItems = watch('items');

  // Calculate total for each item and grand total
  const calculateItemTotal = (index: number): number => {
    const item = watchedItems[index];
    if (item && item.quantity && item.unit_price) {
      return parseFloat(String(item.quantity)) * parseFloat(String(item.unit_price));
    }
    return 0;
  };

  const calculateGrandTotal = (): number => {
    return watchedItems.reduce((sum, _, index) => {
      return sum + calculateItemTotal(index);
    }, 0);
  };

  // Update item total when quantity or unit_price changes
  const handleItemChange = (
    index: number, 
    field: 'quantity' | 'unit_price', 
    value: string
  ): void => {
    const currentItems = watchedItems;
    const updatedItems = [...currentItems];
    updatedItems[index] = {
      ...updatedItems[index],
      [field]: parseFloat(value) || 0,
      total: 0, // Will be recalculated
    };
    
    // Recalculate total
    updatedItems[index].total = calculateItemTotal(index);
  };

  const onFormSubmit = (data: ProformaFormData): void => {
    // Ensure all totals are calculated
    const itemsWithTotals = data.items.map((item, index) => ({
      ...item,
      total: calculateItemTotal(index),
    }));
    
    onSubmit({
      ...data,
      items: itemsWithTotals,
      amount: calculateGrandTotal(),
    });
  };

  return (
    <form onSubmit={handleSubmit(onFormSubmit)} className="proforma-form">
      <div className="form-section">
        <h3>Proforma Invoice Details</h3>
        
        {/* Vendor Field */}
        <div className="form-group">
          <label htmlFor="vendor">
            Vendor Name <span className="required">*</span>
          </label>
          <input
            id="vendor"
            type="text"
            {...register('vendor')}
            className={errors.vendor ? 'error' : ''}
            placeholder="Enter vendor name"
          />
          {errors.vendor && (
            <span className="error-message">{errors.vendor.message}</span>
          )}
        </div>

        {/* Items Section */}
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <label>
              Items <span className="required">*</span>
            </label>
            <button
              type="button"
              onClick={() => append({ name: '', quantity: 1, unit_price: 0, total: 0 })}
              className="btn btn-secondary"
              style={{ padding: '8px 16px' }}
            >
              + Add Item
            </button>
          </div>

          <div className="items-table-container">
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: '40%' }}>Item Name</th>
                  <th style={{ width: '15%' }}>Quantity</th>
                  <th style={{ width: '20%' }}>Unit Price (RWF)</th>
                  <th style={{ width: '20%' }}>Total (RWF)</th>
                  <th style={{ width: '5%' }}></th>
                </tr>
              </thead>
              <tbody>
                {fields.map((field, index) => (
                  <tr key={field.id}>
                    <td>
                      <input
                        type="text"
                        {...register(`items.${index}.name`)}
                        className={errors.items?.[index]?.name ? 'error' : ''}
                        placeholder="Item name"
                        style={{ width: '100%', padding: '8px' }}
                      />
                      {errors.items?.[index]?.name && (
                        <span className="error-message" style={{ fontSize: '12px', display: 'block' }}>
                          {errors.items[index]?.name?.message}
                        </span>
                      )}
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        {...register(`items.${index}.quantity`, { valueAsNumber: true })}
                        onChange={(e) => {
                          handleItemChange(index, 'quantity', e.target.value);
                        }}
                        className={errors.items?.[index]?.quantity ? 'error' : ''}
                        style={{ width: '100%', padding: '8px' }}
                      />
                      {errors.items?.[index]?.quantity && (
                        <span className="error-message" style={{ fontSize: '12px', display: 'block' }}>
                          {errors.items[index]?.quantity?.message}
                        </span>
                      )}
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        {...register(`items.${index}.unit_price`, { valueAsNumber: true })}
                        onChange={(e) => {
                          handleItemChange(index, 'unit_price', e.target.value);
                        }}
                        className={errors.items?.[index]?.unit_price ? 'error' : ''}
                        style={{ width: '100%', padding: '8px' }}
                      />
                      {errors.items?.[index]?.unit_price && (
                        <span className="error-message" style={{ fontSize: '12px', display: 'block' }}>
                          {errors.items[index]?.unit_price?.message}
                        </span>
                      )}
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        value={calculateItemTotal(index).toFixed(2)}
                        readOnly
                        style={{ width: '100%', padding: '8px', background: '#f5f5f5', border: '1px solid #ddd' }}
                      />
                    </td>
                    <td>
                      {fields.length > 1 && (
                        <button
                          type="button"
                          onClick={() => remove(index)}
                          className="btn btn-danger"
                          style={{ padding: '5px 10px', fontSize: '12px' }}
                        >
                          ×
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3} style={{ textAlign: 'right', fontWeight: 'bold', padding: '15px' }}>
                    Grand Total:
                  </td>
                  <td style={{ fontWeight: 'bold', padding: '15px' }}>
                    RWF {calculateGrandTotal().toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
            {errors.items && typeof errors.items.message === 'string' && (
              <span className="error-message">{errors.items.message}</span>
            )}
          </div>
        </div>

        {/* Terms Field */}
        <div className="form-group">
          <label htmlFor="terms">Payment Terms</label>
          <textarea
            id="terms"
            {...register('terms')}
            rows={3}
            placeholder="Enter payment terms (e.g., Net 30 days)"
            style={{ width: '100%', padding: '8px', fontFamily: 'inherit' }}
          />
        </div>

        {/* Form Actions */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '20px', justifyContent: 'flex-end' }}>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="btn btn-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
          >
            {isLoading ? 'Saving...' : 'Save Proforma'}
          </button>
        </div>
      </div>

      <style>{`
        .proforma-form {
          width: 100%;
        }
        .form-section {
          background: white;
          padding: 24px;
          border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        .form-section h3 {
          margin: 0 0 24px 0;
          font-size: 20px;
          font-weight: 600;
          color: #1a1a1a;
        }
        .form-group {
          margin-bottom: 24px;
        }
        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: #374151;
          font-size: 14px;
        }
        .required {
          color: #ef4444;
        }
        .form-group input[type="text"],
        .form-group input[type="number"],
        .form-group textarea {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .form-group input:focus,
        .form-group textarea:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        .form-group input.error,
        .form-group textarea.error {
          border-color: #ef4444;
        }
        .error-message {
          color: #ef4444;
          font-size: 12px;
          margin-top: 4px;
          display: block;
        }
        .items-table-container {
          overflow-x: auto;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
        }
        .items-table-container table {
          width: 100%;
          border-collapse: collapse;
        }
        .items-table-container thead {
          background: #f9fafb;
        }
        .items-table-container th {
          padding: 12px;
          text-align: left;
          font-weight: 600;
          font-size: 12px;
          text-transform: uppercase;
          color: #6b7280;
          border-bottom: 1px solid #e5e7eb;
        }
        .items-table-container td {
          padding: 8px;
          border-bottom: 1px solid #e5e7eb;
        }
        .items-table-container tbody tr:hover {
          background: #f9fafb;
        }
        .items-table-container tfoot {
          background: #f9fafb;
          border-top: 2px solid #e5e7eb;
        }
        .items-table-container tfoot td {
          font-size: 16px;
        }
      `}</style>
    </form>
  );
};

export default ProformaInvoiceForm;

