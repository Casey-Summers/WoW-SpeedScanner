$(document).ready(function () {

    // Show/hide realm input depending on selected mode
    $('input[name="scan_mode"]').on('change', function () {
        const mode = $('input[name="scan_mode"]:checked').val();
        $('#single-realm-input').toggle(mode === 'single');
    });

    // Custom sort for ilvl column using data-order
    jQuery.extend(jQuery.fn.dataTable.ext.type.order, {
        "ilvl-pre": function (data) {
            const span = document.createElement("span");
            span.innerHTML = data;
            const raw = span.querySelector("span")?.getAttribute("data-order") || "0";
            return parseInt(raw, 10);
        },
        "ilvl-asc": function (a, b) {
            return a - b;
        },
        "ilvl-desc": function (a, b) {
            return b - a;
        }
    });

    // Register custom type for buyout sorting
    jQuery.extend(jQuery.fn.dataTable.ext.type.order, {
        "buyout-pre": function (data) {
            const span = document.createElement("span");
            span.innerHTML = data;
            const raw = span.querySelector("span")?.getAttribute("data-order") || "0";
            return parseInt(raw, 10);
        },
        "buyout-asc": function (a, b) {
            return a - b;
        },
        "buyout-desc": function (a, b) {
            return b - a;
        }
    });

    // === Stat mode toggle ===
    $('#statModeSwitch').on('change', function () {
        const isAdvanced = $(this).is(':checked');
        $('#statModeLabel').text(`Mode: ${isAdvanced ? 'Advanced' : 'Normal'}`);
        $('#stat-normal-mode').toggle(!isAdvanced);
        $('#stat-advanced-mode').toggle(isAdvanced);
    });

    // === 'All Stats' logic ===
    $('#all-stats').on('change', function () {
        const isAll = $(this).is(':checked');
        if (isAll) {
            $('.stat-check').prop('checked', false).prop('disabled', true);
        } else {
            $('.stat-check').prop('disabled', false);
        }
    });

    // === Stat check auto-toggle 'All Stats' ===
    $('.stat-check').on('change', function () {
        const checked = $('.stat-check:checked');
        if (checked.length > 2) {
            this.checked = false;
            alert('You can select up to 2 stats.');
            return;
        }

        if (checked.length === 0) {
            $('#all-stats').prop('checked', true);
            $('.stat-check').prop('disabled', true);
        } else {
            $('#all-stats').prop('checked', false);
            $('.stat-check').prop('disabled', false);
        }
    });

    $('#gearTable').DataTable({
        columnDefs: [
            { targets: 7, type: "ilvl" },      // ilvl column custom sort
            { targets: 8, type: "buyout" }     // buyout custom sort
        ],
        order: [],
        autoWidth: false
    });

    let activeSlots = new Set();
    let activeArmorTypes = new Set();

    $('.slot-button').click(function () {
        const slot = $(this).data('slot');
        const type = $(this).data('type');

        $(this).toggleClass('active');

        if (slot) {
            if (activeSlots.has(slot)) {
                activeSlots.delete(slot);
            } else {
                activeSlots.add(slot);
            }
        }

        if (type) {
            if (activeArmorTypes.has(type)) {
                activeArmorTypes.delete(type);
            } else {
                activeArmorTypes.add(type);
            }
        }
    });

    $('#scanForm').on('submit', function (e) {
        e.preventDefault();
        $('#scanStatus').html('⏳ Running scan...');

        const scan_mode = $('input[name="scan_mode"]:checked').val();
        if (scan_mode === "single") {
            config.scan_mode = "single";
            config.realm = $('#realm_input').val().trim();
        } else {
            config.scan_mode = "all";
        }

        const config = {
            haste: $('#haste').is(':checked'),
            crit: $('#crit').is(':checked'),
            vers: $('#vers').is(':checked'),
            mastery: $('#mastery').is(':checked'),
            speed: $('#speed').is(':checked'),
            prismatic: $('#prismatic').is(':checked'),
            min_ilvl: $('input[name="min_ilvl"]').val(),
            max_ilvl: $('input[name="max_ilvl"]').val(),
            max_buyout: $('input[name="max_buyout"]').val(),
            slots: Array.from(activeSlots),
            armor_types: Array.from(activeArmorTypes)
        };

        // Stat distribution logic
        const isAdvanced = $('#statModeSwitch').is(':checked');
        if (isAdvanced) {
            config.stat_mode = "advanced";
            config.STAT_DISTRIBUTION_THRESHOLDS = {
                Haste: parseInt($('#haste-val').val()) || 0,
                Crit: parseInt($('#crit-val').val()) || 0,
                Vers: parseInt($('#vers-val').val()) || 0,
                Mastery: parseInt($('#mastery-val').val()) || 0
            };
        } else {
            config.stat_mode = "normal";
            const selectedStats = $('.stat-check:checked').map(function () {
                return $(this).val();
            }).get();

            if (!$('#all-stats').is(':checked') && selectedStats.length > 0) {
                config.FILTER_TYPE = selectedStats;
            }
            // Else: skip FILTER_TYPE to mean 'search all'
        }

        $.ajax({
            type: 'POST',
            url: '/scan',
            contentType: 'application/json',
            data: JSON.stringify(config),
            success: function (response) {
                if (response.success) {
                    $('#scanStatus').html('✅ Scan complete. Reloading...');
                    setTimeout(() => reloadTable(true), 1000);
                } else {
                    $('#scanStatus').html('❌ Scan failed: ' + response.error);
                }
            },
            error: function () {
                $('#scanStatus').html('❌ AJAX error');
            }
        });
    });

    // === Reloads table from backend data ===
    function reloadTable(showStatus = false) {
        $.get('/reload', function (data) {
            const table = $('#gearTable').DataTable();
            table.clear();
            for (const row of data) {
                // Format helpers
                function formatStat(stat) {
                    return stat.includes("Max") ? `<span class="stat-max">${stat}</span>` : stat;
                }

                function formatIlvl(ilvl) {
                    return `<span class="stat-ilvl">${ilvl}</span>`;
                }

                function formatBuyout(buyout) {
                    if (!buyout) return "";
                    const formatted = buyout.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "'");
                    return `<span class="stat-buyout">${formatted}g</span>`;
                }

                table.row.add([
                    row.realm,
                    row.item_id,
                    row.type,
                    row.slot,
                    formatStat(row.stat1),
                    formatStat(row.stat2),
                    row.name,
                    `<span class="stat-ilvl" data-order="${row.ilvl}">${formatIlvl(row.ilvl)}</span>`,
                    `<span class="stat-buyout" data-order="${row.buyout_gold}">${formatBuyout(row.buyout_gold)}</span>`
                ]);
            }
            table.draw();
            if (showStatus) {
                $('#scanStatus').html('✅ Data refreshed.');
            }
        });
    }

    function applyPreset(presetName) {
        const preset = presets[presetName];
        if (!preset) return;

        // === Reset all stat filters ===
        $("#scanForm input[type='checkbox']").prop("checked", false);
        $('.stat-check').prop("disabled", false);  // Re-enable by default

        // === Apply stat checkboxes ===
        for (let key of ["haste", "crit", "vers", "mastery", "speed", "prismatic"]) {
            if (preset[key]) {
                $(`#${key}`).prop("checked", true);
            }
        }

        // === Handle 'All Stats' logic ===
        const anyStatChecked = ["haste", "crit", "vers", "mastery"].some(stat => preset[stat]);
        $('#all-stats').prop("checked", !anyStatChecked);
        $('.stat-check').prop("disabled", !anyStatChecked);

        // === Apply ilvl and buyout values ===
        $("input[name='min_ilvl']").val(preset.min_ilvl || "");
        $("input[name='max_ilvl']").val(preset.max_ilvl || "");
        $("input[name='max_buyout']").val(preset.max_buyout || "");

        // === Reset all slot/armor buttons ===
        $(".slot-button").removeClass("active");
        activeSlots.clear();
        activeArmorTypes.clear();

        // === Apply slot buttons ===
        for (let slot of preset.slots || []) {
            const btn = $(`.slot-button[data-slot='${slot}']`);
            if (btn.length) {
                btn.addClass("active");
                activeSlots.add(slot);
            }
        }

        // === Apply armor types ===
        for (let type of preset.armor_types || []) {
            const btn = $(`.slot-button[data-type='${type}']`);
            if (btn.length) {
                btn.addClass("active");
                activeArmorTypes.add(type);
            }
        }
    }

    $('.btn-preset').click(function () {
        $('.btn-preset').removeClass('active');
        $(this).addClass('active');
        const presetName = $(this).data('preset');
        applyPreset(presetName);
    });

    // Initial table load
    reloadTable(false); // Do not show message on initial page load

});

const presets = {
    full: {
        haste: false, crit: false, vers: false, mastery: false,
        speed: true, prismatic: true,
        min_ilvl: 0,
        max_ilvl: 1000,
        max_buyout: 10000000,
        slots: [
            "Head", "Chest", "Shoulder", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet",
            "One-Hand", "Two-Hand", "Main-Hand", "Held In Off-hand", "Off-Hand", "Off Hand", "Ranged", "Ranged Right",
            "Finger", "Trinket", "Held In Off-hand", "Neck"
        ],
        armor_types: ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        weapon_types: ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Off-Hand", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand", "Off Hand", "Ranged Right"]
    },

    custom: {
        haste: true, crit: false, vers: false, mastery: false,
        speed: true, prismatic: true,
        min_ilvl: 320,
        max_ilvl: 357,
        max_buyout: 10000000,
        slots: [
            "Waist", "Legs", "Wrist", "Hands", "Back", "Feet",
            "One-Hand", "Two-Hand", "Main-Hand", "Off-Hand",
            "Finger", "Trinket", "Held In Off-hand"
        ],
        armor_types: ["Cloth", "Leather", "Miscellaneous"],
        weapon_types: ["Dagger", "Mace", "Fist Weapon", "Polearm", "Staff", "Off Hand"]
    },

    profitable: {
        haste: false, crit: false, vers: false, mastery: false,
        speed: true, prismatic: true,
        min_ilvl: 580,
        max_ilvl: 1000,
        max_buyout: 2000,
        slots: [
            "Waist", "Legs", "Wrist", "Hands", "Back",
            "One-Hand", "Two-Hand", "Main-Hand", "Held In Off-hand", "Off-Hand", "Off Hand", "Ranged", "Ranged Right",
            "Finger", "Trinket", "Held In Off-hand"
        ],
        armor_types: ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        weapon_types: ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Off-Hand", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand", "Off Hand", "Ranged Right"]
    }
};