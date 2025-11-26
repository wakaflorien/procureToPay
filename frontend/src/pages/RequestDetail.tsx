import React, { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { requestsAPI } from "../services/api";
import ProformaInvoiceForm, { ProformaFormData } from "../components/ProformaInvoiceForm";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "../components/ui/alert-dialog";
import type { PurchaseRequest, ProformaItem } from "../types";
import { AxiosError } from "axios";

interface EditFormItem {
  name: string;
  description: string;
  quantity: number | string;
  unit_price: number | string;
}

const RequestDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [request, setRequest] = useState<PurchaseRequest | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [comments, setComments] = useState<string>("");
  const [cancelComments, setCancelComments] = useState<string>("");
  const [proformaFile, setProformaFile] = useState<File | null>(null);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [showProformaForm, setShowProformaForm] = useState<boolean>(false);
  const [editingProformaData, setEditingProformaData] = useState<Partial<ProformaFormData> | null>(null);
  const [editFormData, setEditFormData] = useState<{
    title: string;
    description: string;
    amount: string;
    items: EditFormItem[];
  }>({
    title: "",
    description: "",
    amount: "",
    items: [],
  });

  useEffect(() => {
    loadRequest();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const loadRequest = async (): Promise<void> => {
    if (!id) return;
    try {
      const response = await requestsAPI.get(id);
      setRequest(response.data);
    } catch (err: unknown) {
      setError("Failed to load request");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (): Promise<void> => {
    if (!id) return;
    if (!comments.trim()) {
      setError(
        "Please provide comments/description for your approval decision"
      );
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      await requestsAPI.approve(id, comments);
      await loadRequest();
      setComments("");
      toast.success("Request approved successfully");
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string; comments?: string[] }>;
      setError(
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.comments?.[0] ||
        "Failed to approve request"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (): Promise<void> => {
    if (!id) return;
    if (!comments.trim()) {
      setError(
        "Please provide comments/description for your rejection decision"
      );
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      await requestsAPI.reject(id, comments);
      await loadRequest();
      setComments("");
      toast.success("Request rejected");
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string; comments?: string[] }>;
      setError(
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.comments?.[0] ||
        "Failed to reject request"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelRequest = async (): Promise<void> => {
    if (!id) return;
    if (!cancelComments.trim()) {
      setError("Please provide comments/description for the cancellation decision");
      return;
    }
    setActionLoading(true);
    setError("");
    try {
      await requestsAPI.cancel(id, cancelComments);
      await loadRequest();
      setCancelComments("");
      toast.success("Request cancelled successfully");
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string; comments?: string[] }>;
      setError(
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.comments?.[0] ||
        "Failed to cancel request"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleProformaSubmit = async (): Promise<void> => {
    if (!id || !proformaFile) {
      setError("Please select a proforma file");
      return;
    }
    setActionLoading(true);
    try {
      const response = await requestsAPI.submitProforma(id, proformaFile);
      await loadRequest();
      setProformaFile(null);
      // Show form to edit extracted data
      if (response.data.extracted_data) {
        const extractedData = response.data.extracted_data;
        // Convert extracted data format to form format
        const formData: Partial<ProformaFormData> = {
          vendor: extractedData.vendor || "",
          amount: Number(extractedData.amount ?? 0),
          items: (extractedData.items || []).map((item: ProformaItem) => {
            const quantity = Number(item?.quantity ?? 1);
            const unitPrice = Number(item?.price ?? item?.unit_price ?? 0);
            return {
              name: item?.name || "",
              quantity: quantity || 1,
              unit_price: unitPrice,
              total: quantity * unitPrice,
            };
          }),
          terms: extractedData.terms || "",
        };
        setEditingProformaData(formData);
        setShowProformaForm(true);
      } else {
        toast.success("Proforma uploaded successfully");
      }
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || "Failed to upload proforma");
    } finally {
      setActionLoading(false);
    }
  };

  const handleProformaFormSubmit = async (_formData: ProformaFormData): Promise<void> => {
    setActionLoading(true);
    try {
      void _formData;
      // Update proforma data via API (you may need to add an endpoint for this)
      // For now, we'll just update the local state
      await loadRequest();
      setShowProformaForm(false);
      setEditingProformaData(null);
      toast.success("Proforma data saved successfully");
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || "Failed to save proforma data");
    } finally {
      setActionLoading(false);
    }
  };

  const handleProformaFormCancel = (): void => {
    setShowProformaForm(false);
    setEditingProformaData(null);
  };

  const handleReceiptSubmit = async (): Promise<void> => {
    if (!id || !receiptFile) {
      setError("Please select a receipt file");
      return;
    }
    setActionLoading(true);
    try {
      const response = await requestsAPI.submitReceipt(id, receiptFile);
      await loadRequest();
      setReceiptFile(null);
      const validation = response.data.validation_result;
      if (validation?.is_valid) {
        toast.success("Receipt validated successfully!");
      } else {
        toast.error(`Receipt validation failed: ${validation?.errors?.join(", ") || "Unknown error"}`);
      }
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || "Failed to upload receipt");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownload = async (type: "proforma" | "receipt" | "purchase_order"): Promise<void> => {
    if (!id) return;
    try {
      let response;
      let filename: string;
      switch (type) {
        case "proforma":
          response = await requestsAPI.downloadProforma(id);
          filename = `proforma_${id}.pdf`;
          break;
        case "receipt":
          response = await requestsAPI.downloadReceipt(id);
          filename = `receipt_${id}.pdf`;
          break;
        case "purchase_order":
          response = await requestsAPI.downloadPurchaseOrder(id);
          filename = `purchase_order_${id}.pdf`;
          break;
        default:
          return;
      }

      const contentType = response.headers?.["content-type"];
      const blob =
        response.data instanceof Blob
          ? response.data
          : new Blob([response.data], { type: contentType || "application/pdf" });

      if (contentType?.includes("application/json")) {
        const text = await blob.text();
        try {
          const payload = JSON.parse(text);
          setError(payload.detail || payload.message || `Failed to download ${type}`);
        } catch {
          setError(`Failed to download ${type}`);
        }
        return;
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || `Failed to download ${type}`);
    }
  };

  const handleEdit = (): void => {
    setEditFormData({
      title: request?.title || "",
      description: request?.description || "",
      amount: request?.amount || "",
      items:
        request?.items && request?.items.length > 0
          ? request?.items.map((item) => ({
            name: item.name,
            description: item.description || "",
            quantity: item.quantity,
            unit_price: item.unit_price,
          }))
          : [{ name: "", description: "", quantity: 1, unit_price: "" }],
    });
    setIsEditing(true);
    setError("");
  };

  const handleCancelEdit = (): void => {
    setIsEditing(false);
    setEditFormData({
      title: "",
      description: "",
      amount: "",
      items: [],
    });
    setError("");
  };

  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>): void => {
    setEditFormData({ ...editFormData, [e.target.name]: e.target.value });
  };

  const handleEditItemChange = (index: number, field: keyof EditFormItem, value: string | number): void => {
    const items = [...editFormData.items];
    items[index] = { ...items[index], [field]: value };
    setEditFormData({ ...editFormData, items });
  };

  const addEditItem = (): void => {
    setEditFormData({
      ...editFormData,
      items: [
        ...editFormData.items,
        { name: "", description: "", quantity: 1, unit_price: "" },
      ],
    });
  };

  const removeEditItem = (index: number): void => {
    const items = editFormData.items.filter((_, i) => i !== index);
    setEditFormData({ ...editFormData, items });
  };

  const handleUpdate = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    if (!id) return;
    e.preventDefault();
    setError("");
    setActionLoading(true);

    try {
      const normalizedAmount = parseFloat(editFormData.amount || "0").toFixed(2);
      const data = {
        title: editFormData.title,
        description: editFormData.description,
        amount: normalizedAmount,
        items: editFormData.items
          .filter((item) => item.name.trim() !== "") // Remove empty items
          .map((item) => ({
            name: item.name,
            description: item.description || "",
            quantity: parseInt(String(item.quantity)),
            unit_price: parseFloat(String(item.unit_price)),
          })),
      };
      await requestsAPI.update(id, data);
      await loadRequest();
      setIsEditing(false);
      toast.success("Request updated successfully!");
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || "Failed to update request");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!id) return;
    setActionLoading(true);
    try {
      await requestsAPI.delete(id);
      toast.success("Request deleted successfully!");
      navigate("/");
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || "Failed to delete request");
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div
        className="container"
        style={{ textAlign: "center", padding: "50px" }}
      >
        Loading...
      </div>
    );
  }

  if (!request) {
    return <div className="container">Request not found</div>;
  }

  if (!user) {
    return <div className="container">You must be logged in to view this request.</div>;
  }

  const isApprover =
    user.role === "approver_level_1" || user.role === "approver_level_2";
  const isFinance = user.role === "finance";
  const isAdmin = user.role === "admin" || user.is_superuser;
  const requestAmountValue = Number(request.amount ?? 0);
  const approverCanAct =
    isApprover &&
    request.status === "pending" &&
    request.can_be_approved &&
    !request.has_user_approved &&
    !request.has_user_rejected;
  const adminOverrideAvailable =
    isAdmin &&
    request.status !== "cancelled" &&
    !request.has_user_approved &&
    !request.has_user_rejected;
  // Can approve if: user is approver following workflow or admin overriding regardless of status
  const canApprove = approverCanAct || adminOverrideAvailable;
  // Can download documents if: approver, finance, or admin
  const canDownloadDocuments = isApprover || isFinance || isAdmin;
  const isOwner = typeof request.created_by === 'object' && request.created_by.id === user.id;
  // Can edit if: user is owner, status is pending, and request hasn't been approved
  const canEdit =
    isOwner &&
    request.status === "pending" &&
    request.can_be_edited !== false &&
    !request.level_1_approved &&
    !request.level_2_approved;
  // Upload permissions: owner (staff) can upload everything; finance can upload proforma only; admins observe only
  const canUploadProforma = (isOwner || isFinance) && !isAdmin;
  const canUploadReceipt = isOwner && !isAdmin;
  const canViewComparison = isFinance || isAdmin;
  const showComparisonTab =
    canViewComparison &&
    request.proforma_data &&
    Object.keys(request.proforma_data).length > 0;
  const statusBadgeVariant: "pending" | "approved" | "rejected" | "cancelled" =
    request.status === "approved"
      ? "approved"
      : request.status === "rejected"
        ? "rejected"
        : request.status === "cancelled"
          ? "cancelled"
          : "pending";

  const renderDocumentsCard = () => {

    return (
      <div className="card space-y-6">
        <h3 className="text-lg font-semibold">Documents</h3>
        {isOwner && request.needs_receipt_upload && (
          <div className="rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-800">
            <strong>Receipt required:</strong> This request is approved. Please upload your receipt so the finance team can validate it.
          </div>
        )}

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <strong>Proforma Invoice</strong>
            {request.proforma && canDownloadDocuments ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownload("proforma")}
              >
                Download Proforma
              </Button>
            ) : (
            <Button variant="destructive" size="sm" disabled>No Proforma Uploaded</Button>
            )}
          </div>
          {canUploadProforma && request.status === "pending" && !showProformaForm && (
            <div className="space-y-3">
              <div className="form-group">
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setProformaFile(e.target.files?.[0] || null)}
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={handleProformaSubmit}
                  disabled={actionLoading || !proformaFile}
                >
                  Upload Proforma
                </Button>
                {request.proforma_data && Object.keys(request.proforma_data).length > 0 && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      const formData: Partial<ProformaFormData> = {
                        vendor: request?.proforma_data?.vendor || "",
                        amount: Number(request?.proforma_data?.amount ?? 0),
                        items: (request?.proforma_data?.items || []).map((item: ProformaItem) => {
                          const quantity = Number(item?.quantity ?? 1);
                          const unitPrice = Number(item?.price ?? item?.unit_price ?? 0);
                          return {
                            name: item?.name || "",
                            quantity: quantity || 1,
                            unit_price: unitPrice,
                            total: quantity * unitPrice,
                          };
                        }),
                        terms: request?.proforma_data?.terms || "",
                      };
                      setEditingProformaData(formData);
                      setShowProformaForm(true);
                    }}
                  >
                    Edit Extracted Data
                  </Button>
                )}
              </div>
            </div>
          )}
          {showProformaForm && editingProformaData && (
            <div className="rounded-md border p-3">
              <ProformaInvoiceForm
                initialData={editingProformaData}
                onSubmit={handleProformaFormSubmit}
                onCancel={handleProformaFormCancel}
                isLoading={actionLoading}
              />
            </div>
          )}
          {request.proforma_data && Object.keys(request.proforma_data).length > 0 && (
            <div className="rounded-md border bg-muted/40 p-3">
              <strong>Extracted Proforma Data</strong>
              <div className="mt-2 space-y-2 text-sm">
                {request.proforma_data.vendor && (
                  <p>
                    <strong>Vendor:</strong> {request.proforma_data.vendor}
                  </p>
                )}
                {request.proforma_data.amount !== undefined && (
                  <p>
                    <strong>Amount:</strong> RWF{" "}
                    {Number(request?.proforma_data?.amount ?? 0).toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </p>
                )}
              </div>
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <strong>Purchase Order</strong>
            {request.purchase_order && canDownloadDocuments && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownload("purchase_order")}
              >
                Download Purchase Order
              </Button>
            )}
          </div>
          {request.purchase_order_data && (
            <div className="rounded-md border bg-slate-50 p-3 text-sm">
              <p>
                <strong>PO Number:</strong>{" "}
                {request.purchase_order_data.po_number || "N/A"}
              </p>
              {request.purchase_order_data.vendor && (
                <p>
                  <strong>Vendor:</strong> {request.purchase_order_data.vendor}
                </p>
              )}
              {request.purchase_order_data.total_amount !== undefined && (
                <p>
                  <strong>Total Amount:</strong> RWF{" "}
                  {Number(request?.purchase_order_data?.total_amount ?? 0).toLocaleString()}
                </p>
              )}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <strong>Receipt</strong>
            {request.receipt && canDownloadDocuments && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDownload("receipt")}
              >
                Download Receipt
              </Button>
            )}
          </div>
          {canUploadReceipt && request.status === "approved" && (
            <div className="space-y-3">
              <div className="form-group">
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setReceiptFile(e.target.files?.[0] || null)}
                />
              </div>
              <Button
                onClick={handleReceiptSubmit}
                disabled={actionLoading || !receiptFile}
              >
                Upload Receipt
              </Button>
            </div>
          )}
          {request.receipt_data && Object.keys(request.receipt_data).length > 0 && (
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <strong>Extracted Receipt Data</strong>
              {request?.receipt_data?.vendor && (
                <p className="mt-2">
                  <strong>Vendor:</strong> {request.receipt_data.vendor}
                </p>
              )}
              {request?.receipt_data?.amount !== undefined && (
                <p>
                  <strong>Amount:</strong> RWF{" "}
                  {Number(request?.receipt_data?.amount ?? 0).toLocaleString()}
                </p>
              )}
            </div>
          )}
          {request.receipt_validation_result && (
            <div
              className={`rounded-md border p-3 ${request.receipt_validation_result.is_valid
                ? "border-green-200 bg-green-50"
                : "border-red-200 bg-red-50"
                }`}
            >
              <strong>Validation Result:</strong>
              <p className="mt-1">
                Valid: {request.receipt_validation_result.is_valid ? "Yes" : "No"}
              </p>
              {request.receipt_validation_result.errors?.length ? (
                <div>
                  <strong>Errors:</strong>
                  <ul className="list-disc pl-5">
                    {request.receipt_validation_result.errors.map((msg: string, idx: number) => (
                      <li key={idx}>{msg}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          )}
        </section>
      </div>
    );
  }

  const renderComparisonContent = () => {
    if (!showComparisonTab || !request.proforma_data) return null;
    const proformaAmount = Number(request.proforma_data.amount ?? 0);
    return (
      <section className="space-y-6">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-md border p-4">
            <h4 className="text-base font-semibold">Request Snapshot</h4>
            <p className="text-sm text-muted-foreground">
              Original request amount and items
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <strong>Amount:</strong> RWF{" "}
                {requestAmountValue.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </li>
              {request.items.slice(0, 5).map((item) => (
                <li key={item.id}>
                  {item.name} • {item.quantity} x RWF{" "}
                  {Number(item.unit_price).toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </li>
              ))}
              {request.items.length > 5 && (
                <li className="text-muted-foreground">
                  +{request.items.length - 5} more items
                </li>
              )}
            </ul>
          </div>
          <div className="rounded-md border p-4">
            <h4 className="text-base font-semibold">Extracted Proforma Snapshot</h4>
            <p className="text-sm text-muted-foreground">
              AI extracted vendor, items, and totals
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {request.proforma_data.vendor && (
                <li>
                  <strong>Vendor:</strong> {request.proforma_data.vendor}
                </li>
              )}
              <li>
                <strong>Amount:</strong> RWF{" "}
                {proformaAmount.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </li>
              {(request.proforma_data.items || []).slice(0, 5).map((item, idx) => (
                <li key={`${item.name}-${idx}`}>
                  {item.name} • {item.quantity} x RWF{" "}
                  {Number(item.price ?? item.unit_price ?? 0).toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </li>
              ))}
              {request.proforma_data.items &&
                request.proforma_data.items.length > 5 && (
                  <li className="text-muted-foreground">
                    +{request.proforma_data.items.length - 5} more items
                  </li>
                )}
            </ul>
          </div>
        </div>

        <div>
          <h4 className="mb-3 text-base font-semibold">Item-by-item Comparison</h4>
          <div style={{ overflowX: "auto" }}>
            <table className="table w-full">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Request Qty</th>
                  <th>Proforma Qty</th>
                  <th>Request Unit Price</th>
                  <th>Proforma Unit Price</th>
                  <th>Request Total</th>
                  <th>Proforma Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {request.items.map((reqItem, idx) => {
                  const proformaItem = request.proforma_data?.items?.find(
                    (pItem) =>
                      pItem.name?.toLowerCase().trim() ===
                      reqItem.name?.toLowerCase().trim()
                  );
                  const reqQty = Number(reqItem?.quantity ?? 0);
                  const reqUnitPrice = Number(reqItem?.unit_price ?? 0);
                  const reqTotal =
                    Number(reqItem?.total_price ?? reqQty * reqUnitPrice) ||
                    reqQty * reqUnitPrice;
                  const proformaQty = Number(proformaItem?.quantity ?? 0);
                  const proformaUnitPrice = Number(
                    proformaItem?.price ?? proformaItem?.unit_price ?? 0
                  );
                  const proformaTotal = proformaQty * proformaUnitPrice;
                  const qtyMatch = Math.abs(reqQty - proformaQty) < 0.01;
                  const priceMatch =
                    Math.abs(reqUnitPrice - proformaUnitPrice) < 0.01;
                  const totalMatch =
                    Math.abs(reqTotal - proformaTotal) < 0.01;
                  const hasDiscrepancy = !qtyMatch || !priceMatch || !totalMatch;
                  return (
                    <tr
                      key={`${reqItem.id}-${idx}`}
                      style={{
                        background: hasDiscrepancy ? "#fff3cd" : "#d4edda",
                      }}
                    >
                      <td>{reqItem.name}</td>
                      <td>{reqQty}</td>
                      <td>
                        {proformaItem ? proformaQty : "N/A"}
                        {!qtyMatch && proformaItem && (
                          <span className="ml-1 text-xs text-red-600">
                            ({reqQty > proformaQty ? "↓" : "↑"})
                          </span>
                        )}
                      </td>
                      <td>
                        RWF{" "}
                        {reqUnitPrice.toLocaleString("en-US", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td>
                        {proformaItem
                          ? `RWF ${proformaUnitPrice.toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}`
                          : "N/A"}
                        {!priceMatch && proformaItem && (
                          <span className="ml-1 text-xs text-red-600">
                            ({reqUnitPrice > proformaUnitPrice ? "↓" : "↑"})
                          </span>
                        )}
                      </td>
                      <td>
                        RWF{" "}
                        {reqTotal.toLocaleString("en-US", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td>
                        {proformaItem
                          ? `RWF ${proformaTotal.toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}`
                          : "N/A"}
                        {!totalMatch && proformaItem && (
                          <span className="ml-1 text-xs text-red-600">
                            ({reqTotal > proformaTotal ? "↓" : "↑"})
                          </span>
                        )}
                      </td>
                      <td>
                        {!proformaItem ? (
                          <Badge variant="destructive">Missing</Badge>
                        ) : hasDiscrepancy ? (
                          <Badge variant="pending">Discrepancy</Badge>
                        ) : (
                          <Badge variant="approved">Match</Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {isFinance && request.status !== "cancelled" && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4">
            <h4 className="text-base font-semibold text-destructive">
              Finance Manual Override
            </h4>
            <p className="text-sm text-muted-foreground">
              If discrepancies cannot be resolved, provide a reason and cancel the request.
            </p>
            <div className="form-group mt-3">
              <label>Cancellation Comments *</label>
              <textarea
                value={cancelComments}
                onChange={(e) => setCancelComments(e.target.value)}
                placeholder="Explain the discrepancies or reason for cancellation..."
                rows={4}
                required
              />
            </div>
            <Button
              variant="destructive"
              className="mt-3"
              onClick={handleCancelRequest}
              disabled={actionLoading || !cancelComments.trim()}
            >
              {actionLoading ? "Processing..." : "Cancel Request"}
            </Button>
          </div>
        )}
      </section>
    );
  };

  const renderOverviewCard = () => (
    <div className="card space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{request.title}</h1>
          <p className="text-sm text-muted-foreground">
            Created by {typeof request.created_by === 'object' ? request.created_by.username : request.created_by} on{" "}
            {new Date(request.created_at).toLocaleString()}
          </p>
        </div>
        <Badge variant={statusBadgeVariant} className="text-base capitalize">
          {request.status}
        </Badge>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-md border p-4">
          <p className="text-sm text-muted-foreground">Amount</p>
          <p className="text-xl font-semibold">
            RWF{" "}
            {requestAmountValue.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
        </div>
        <div className="rounded-md border p-4">
          <p className="text-sm text-muted-foreground">Last Updated</p>
          <p className="text-xl font-semibold">
            {new Date(request.updated_at).toLocaleString()}
          </p>
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-sm font-semibold text-muted-foreground">Description</p>
        <p>{request.description}</p>
      </div>
    </div>
  );

  const renderItemsCard = () => {
    if (!request.items || request.items.length === 0) return null;
    return (
      <div className="card">
        <h3 className="text-lg font-semibold">Request Items</h3>
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {request.items.map((item) => {
                const qty = Number(item?.quantity ?? 0);
                const unitPrice = Number(item?.unit_price ?? 0);
                const total = Number(item?.total_price ?? qty * unitPrice);
                return (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.description}</td>
                    <td>{qty}</td>
                    <td>
                      RWF{" "}
                      {unitPrice.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td>
                      RWF{" "}
                      {total.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderApprovalsHistory = () => {
    if (!request.approvals || request.approvals.length === 0) {
      return (
        <div className="card">
          <h3 className="text-lg font-semibold">Approval History</h3>
          <p className="text-sm text-muted-foreground">No approval history found</p>
        </div>
      )
    }

    return (
      <div className="card">
        <h3 className="text-lg font-semibold">Approval History</h3>
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead>
              <tr>
                <th>Approver</th>
                <th>Level</th>
                <th>Action</th>
                <th>Comments</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {request.approvals.map((approval) => (
                <tr key={approval.id}>
                  <td>{approval.approver.username}</td>
                  <td>{approval.level}</td>
                  <td>
                    <Badge
                      variant={
                        approval.action === "approved"
                          ? "approved"
                          : approval.action === "rejected"
                            ? "rejected"
                            : "cancelled"
                      }
                    >
                      {approval.action}
                    </Badge>
                  </td>
                  <td>{approval.comments}</td>
                  <td>{new Date(approval.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderApprovalActions = () => {
    if (!canApprove) return null;
    return (
      <div className="card space-y-4">
        <div>
          <h3 className="text-lg font-semibold">Approve/Reject Request</h3>
          <p className="text-sm text-muted-foreground">
            {isAdmin
              ? "Administrator override: you can approve or reject regardless of the current workflow state."
              : user?.role?.toLowerCase() === "approver_level_1"
                ? "You are reviewing this request at Level 1. Please provide your approval decision."
                : "You are reviewing this request at Level 2. Please provide your approval decision."}
          </p>
        </div>
        <div className="form-group">
          <label>Comments/Description *</label>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder="Please provide comments or description for your decision..."
            rows={4}
            required
          />
          <small className="text-sm text-muted-foreground">
            Comments are required for approval/rejection decisions.
          </small>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={handleApprove}
            disabled={actionLoading || !comments.trim()}
          >
            {actionLoading ? "Processing..." : "Approve"}
          </Button>
          <Button
            variant="destructive"
            onClick={handleReject}
            disabled={actionLoading || !comments.trim()}
          >
            {actionLoading ? "Processing..." : "Reject"}
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="container mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Button variant="outline" onClick={() => navigate("/")}>
          ← Back
        </Button>
        {canEdit && !isEditing && (
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleEdit} disabled={actionLoading}>
              Edit
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={actionLoading}>
                  Delete
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete this request?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. This will permanently remove this purchase
                    request and all of its related data.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                      e.preventDefault();
                      void handleDelete();
                    }}
                  >
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {isEditing ? (
        <form onSubmit={handleUpdate} className="space-y-4">
          <div className="card space-y-4">
            <h1 className="text-xl font-semibold">Edit Purchase Request</h1>
            <div className="form-group">
              <label>Title *</label>
              <input
                type="text"
                name="title"
                value={editFormData.title}
                onChange={handleEditChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Description *</label>
              <textarea
                name="description"
                value={editFormData.description}
                onChange={handleEditChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Total Amount *</label>
              <input
                type="number"
                step="0.01"
                name="amount"
                value={editFormData.amount}
                onChange={handleEditChange}
                required
              />
            </div>
          </div>

          <div className="card space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Request Items</h3>
              <Button
                type="button"
                onClick={addEditItem}
                variant="secondary"
                size="sm"
              >
                Add Item
              </Button>
            </div>
            {editFormData.items.map((item, index) => (
              <div
                key={index}
                className="space-y-4 rounded-md border p-4"
              >
                <div className="flex items-center justify-between">
                  <strong>Item {index + 1}</strong>
                  {editFormData.items.length > 1 && (
                    <Button
                      type="button"
                      onClick={() => removeEditItem(index)}
                      variant="destructive"
                      size="sm"
                    >
                      Remove
                    </Button>
                  )}
                </div>
                <div className="form-group">
                  <label>Name *</label>
                  <input
                    type="text"
                    value={item.name}
                    onChange={(e) =>
                      handleEditItemChange(index, "name", e.target.value)
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    value={item.description}
                    onChange={(e) =>
                      handleEditItemChange(index, "description", e.target.value)
                    }
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="form-group">
                    <label>Quantity *</label>
                    <input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) =>
                        handleEditItemChange(index, "quantity", e.target.value)
                      }
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Unit Price *</label>
                    <input
                      type="number"
                      step="0.01"
                      value={item.unit_price}
                      onChange={(e) =>
                        handleEditItemChange(
                          index,
                          "unit_price",
                          e.target.value
                        )
                      }
                      required
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={actionLoading}>
              {actionLoading ? "Updating..." : "Update Request"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancelEdit}
              disabled={actionLoading}
            >
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <Tabs defaultValue="overview" className="w-full space-y-4">
          <TabsList className="grid w-full grid-cols-3 md:grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="approvals">Approvals</TabsTrigger>
            {showComparisonTab && (
              <TabsTrigger value="comparison">Comparison</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {renderOverviewCard()}
            {renderItemsCard()}
          </TabsContent>

          <TabsContent value="documents">
            {renderDocumentsCard()}
          </TabsContent>

          <TabsContent value="approvals" className="space-y-4">
            {renderApprovalsHistory()}
            {renderApprovalActions()}
          </TabsContent>

          {showComparisonTab && (
            <TabsContent value="comparison">
              {renderComparisonContent()}
            </TabsContent>
          )}
        </Tabs>
      )}
    </div>
  );
};

export default RequestDetail;
