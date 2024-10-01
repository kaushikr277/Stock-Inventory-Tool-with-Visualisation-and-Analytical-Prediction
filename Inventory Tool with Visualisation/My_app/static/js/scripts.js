// static/scripts.js


$(document).ready(function() {
    $('#inventoryId').on('input', function() {
        let query = $(this).val();
        if (query.length >= 2) {
            $.ajax({
                url: "/search_inventory",
                type: "GET",
                data: { query: query },
                success: function(data) {
                    let inventoryList = $('#inventoryList');
                    inventoryList.empty();

                    if (data.length > 0) {
                        let list = $('<ul></ul>');
                        data.forEach(function(item) {
                            let listItem = $('<li></li>').text(`${item.InventoryID} - ${item.Description} - ${item.ManufacturerNumber} - ${item.SupplierName}`).click(function() {
                                selectInventory(item);
                                inventoryList.empty();
                            });
                            list.append(listItem);
                        });
                        inventoryList.append(list);
                    } else {
                        // If no existing inventory is found, unlock the fields for user input
                        $('#descriptionField').val('').prop('readonly', false);
                        $('#manufacturerNumber').val('').prop('readonly', false);
                        $('#supplierName').val('').prop('readonly', false);
                    }
                }
            });
        } else {
            $('#inventoryList').empty();
            // Unlock the fields if inventory ID input is cleared
            $('#descriptionField').val('').prop('readonly', false);
            $('#manufacturerNumber').val('').prop('readonly', false);
            $('#supplierName').val('').prop('readonly', false);
        }
    });
});

function selectInventory(item) {
    $('#inventoryId').val(item.InventoryID);
    $('#descriptionField').val(item.Description).prop('readonly', true);
    $('#manufacturerNumber').val(item.ManufacturerNumber).prop('readonly', true);
    $('#supplierName').val(item.SupplierName).prop('readonly', false); // Supplier name remains editable

    // Clear the search results
    $('#inventoryList').empty();
}



function fetchSuppliers() {
    let supplierName = $('#supplierName').val();
    if (supplierName.length >= 2) {
        $.ajax({
            url: "/fetch_suppliers",
            type: "GET",
            data: { query: supplierName },
            success: function (data) {
                $('#supplierList').empty();
                let suppliers = data.suppliers;
                if (suppliers.length > 0) {
                    let list = $('<ul></ul>');
                    suppliers.forEach(function (supplier) {
                        let item = $('<li></li>').text(supplier).click(function () {
                            $('#supplierName').val(supplier);
                            $('#supplierList').empty();
                        });
                        list.append(item);
                    });
                    $('#supplierList').append(list);
                }
            }
        });
    } else {
        $('#supplierList').empty();
    }
}

function fetchManufacturers() {
    let manufacturerNumber = $('#manufacturerNumber').val();
    if (manufacturerNumber.length >= 2) {
        $.ajax({
            url: "/fetch_manufacturers",
            type: "GET",
            data: { query: manufacturerNumber },
            success: function (data) {
                $('#manufacturerList').empty();
                let manufacturers = data.manufacturers;
                if (manufacturers.length > 0) {
                    let list = $('<ul></ul>');
                    manufacturers.forEach(function (manufacturer) {
                        let item = $('<li></li>').text(manufacturer).click(function () {
                            $('#manufacturerNumber').val(manufacturer);
                            $('#manufacturerList').empty();
                            // $('#descriptionField').hide();
                        });
                        list.append(item);
                    });
                    $('#manufacturerList').append(list);
                    // $('#descriptionField').hide();
                } 
                //else {
                    // $('#descriptionField').show();
                //}
            }
        });
    } else {
        $('#manufacturerList').empty();
       // $('#descriptionField').show();
    }
}

function fetchdescriptions() {
    let descriptionField = $('#descriptionField').val();
    if (descriptionField.length >= 2) {
        $.ajax({
            url: "/fetch_descriptions",
            type: "GET",
            data: { query: descriptionField},
            success: function (data) {
                $('#descriptionList').empty();
                let descriptions = data.descriptions;
                if (descriptions.length > 0) {
                    let list = $('<ul></ul>');
                    descriptions.forEach(function (description) {
                        let item = $('<li></li>').text(description).click(function () {
                            $('#descriptionField').val(description);
                            $('#descriptionList').empty();
                        });
                        list.append(item);
                    });
                    $('#descriptionList').append(list);
                }
            }
        });
    } else {
        $('#descriptionList').empty();
    }
}

function fetchPurchaseOrders() {
    let purchaseOrderNo = $('#purchaseOrderNo').val();
    if (purchaseOrderNo.length >= 2) {
        $.ajax({
            url: "/fetch_purchase_orders",
            type: "GET",
            data: { query: purchaseOrderNo },
            success: function (data) {
                $('#purchaseOrderList').empty();
                let purchaseOrders = data.purchaseOrders;
                if (purchaseOrders.length > 0) {
                    let list = $('<ul></ul>');
                    purchaseOrders.forEach(function (purchaseOrder) {
                        let item = $('<li></li>').text(purchaseOrder).click(function () {
                            $('#purchaseOrderNo').val(purchaseOrder);
                            $('#purchaseOrderList').empty();
                        });
                        list.append(item);
                    });
                    $('#purchaseOrderList').append(list);
                }
            }
        });
    } else {
        $('#purchaseOrderList').empty();
    }
}

function fetchOrderCodes() {
    let orderCode = $('#orderCode').val();
    if (orderCode.length >= 2) {
        $.ajax({
            url: "/fetch_order_codes",
            type: "GET",
            data: { query: orderCode },
            success: function (data) {
                $('#orderCodeList').empty();
                let orderCodes = data.orderCodes;
                if (orderCodes.length > 0) {
                    let list = $('<ul></ul>');
                    orderCodes.forEach(function (orderCode) {
                        let item = $('<li></li>').text(orderCode).click(function () {
                            $('#orderCode').val(orderCode);
                            $('#orderCodeList').empty();
                        });
                        list.append(item);
                    });
                    $('#orderCodeList').append(list);
                }
            }
        });
    } else {
        $('#orderCodeList').empty();
    }
}

function fetchCategories() {
    let category = $('#category').val();
    if (category.length >= 2) {
        $.ajax({
            url: "/fetch_categories",
            type: "GET",
            data: { query: category },
            success: function (data) {
                $('#categoryList').empty();
                let categories = data.categories;
                if (categories.length > 0) {
                    let list = $('<ul></ul>');
                    categories.forEach(function (category) {
                        let item = $('<li></li>').text(category).click(function () {
                            $('#category').val(category);
                            $('#categoryList').empty();
                        });
                        list.append(item);
                    });
                    $('#categoryList').append(list);
                }
            }
        });
    } else {
        $('#categoryList').empty();
    }
}

let stockIdToDelete;
function showPasswordModal(stockId) {
    stockIdToDelete = stockId;
    document.getElementById('passwordModal').style.display = "block";
}

document.getElementsByClassName('close')[0].onclick = function() {
    document.getElementById('passwordModal').style.display = "none";
}

window.onclick = function(event) {
    if (event.target == document.getElementById('passwordModal')) {
        document.getElementById('passwordModal').style.display = "none";
    }
}

document.getElementById('confirmDeleteButton').onclick = function() {
    const password = document.getElementById('passwordInput').value;
    if (password) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/delete_inventory/${stockIdToDelete}`;

        const passwordField = document.createElement('input');
        passwordField.type = 'hidden';
        passwordField.name = 'password';
        passwordField.value = password;

        const csrfField = document.createElement('input');
        csrfField.type = 'hidden';
        csrfField.name = 'csrf_token';
        csrfField.value = '{{ csrf_token() }}';  // Generate CSRF token

        form.appendChild(passwordField);
        form.appendChild(csrfField);
        document.body.appendChild(form);
        form.submit();
    }
}
function resetFilters() {
const form = document.querySelector('.search-form');
const inputs = form.querySelectorAll('input[type="text"], input[type="number"]');
inputs.forEach(input => input.value = '');
form.submit();
}
