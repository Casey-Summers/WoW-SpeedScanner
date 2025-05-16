$(document).ready(function() {
  $('#gearTable').DataTable();

  let activeSlots = new Set();

  $('.slot-button').click(function () {
    const slot = $(this).data('slot');
    $(this).toggleClass('active');
    if (activeSlots.has(slot)) {
      activeSlots.delete(slot);
    } else {
      activeSlots.add(slot);
    }
  });

  $('#scanForm').on('submit', function (e) {
    e.preventDefault();
    $('#scanStatus').html('⏳ Running scan...');

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
      slots: Array.from(activeSlots)
    };

    $.ajax({
      type: 'POST',
      url: '/scan',
      contentType: 'application/json',
      data: JSON.stringify(config),
      success: function (response) {
        if (response.success) {
          $('#scanStatus').html('✅ Scan complete. Reloading...');
          setTimeout(reloadTable, 1000);
        } else {
          $('#scanStatus').html('❌ Scan failed: ' + response.error);
        }
      },
      error: function () {
        $('#scanStatus').html('❌ AJAX error');
      }
    });
  });

  function reloadTable() {
    $.get('/reload', function (data) {
      const table = $('#gearTable').DataTable();
      table.clear();
      for (const row of data) {
        table.row.add([
          row.realm,
          row.item_id,
          row.type,
          row.slot,
          row.stat1,
          row.stat2,
          row.name,
          row.ilvl,
          row.buyout_gold
        ]);
      }
      table.draw();
      $('#scanStatus').html('✅ Data refreshed.');
    });
  }

  function applyPreset(presetName) {
    const preset = presets[presetName];
    if (!preset) return;

    $("#scanForm input[type='checkbox']").prop("checked", false);

    for (let key of ["haste", "crit", "vers", "mastery", "speed", "prismatic"]) {
      if (preset[key]) {
        $(`#${key}`).prop("checked", true);
      }
    }

    $("input[name='min_ilvl']").val(preset.min_ilvl || "");
    $("input[name='max_ilvl']").val(preset.max_ilvl || "");
    $("input[name='max_buyout']").val(preset.max_buyout || "");

    $(".slot-button").removeClass("active");
    activeSlots.clear();

    for (let slot of preset.slots) {
      const btn = $(`.slot-button[data-slot='${slot}']`);
      if (btn.length) {
        btn.addClass("active");
        activeSlots.add(slot);
      }
    }
  }

  $('.btn-preset').click(function () {
    $('.btn-preset').removeClass('active');
    $(this).addClass('active');
    const presetName = $(this).data('preset');
    applyPreset(presetName);
  });
});

const presets = {
  full: {
    haste: true, crit: true, vers: true, mastery: true, speed: true, prismatic: true,
    min_ilvl: 1,
    max_ilvl: 1000,
    max_buyout: 999999,
    slots: [
      "Head", "Shoulder", "Chest", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet",
      "One-Hand", "Two-Hand", "Main-Hand", "Off-Hand", "Held In Off-hand", "Ranged", "Ranged Right",
      "Finger", "Trinket", "Neck"
    ]
  },
  custom: {
    haste: true, speed: true, prismatic: true,
    min_ilvl: 320,
    max_ilvl: 357,
    max_buyout: 1000000,
    slots: ["Waist", "Legs", "Wrist", "Hands", "Back", "Feet", "One-Hand", "Two-Hand", "Trinket"]
  },
  profitable: {
    speed: true, prismatic: true,
    min_ilvl: 580,
    max_ilvl: 1000,
    max_buyout: 2000,
    slots: ["Waist", "Legs", "Wrist", "Hands", "Back", "Finger", "Trinket"]
  }
};