function selectAll() {
  source = document.getElementById('all-check')
  checkboxes = document.getElementsByClassName('city-check');
  for (var i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = source.checked;
  }
}

function sendNotify() {
  document.getElementsByClassName('btn')[0].disabled = true;
  selected = {};
  checkboxes = document.getElementsByClassName('city-check');
  for (var i = 0; i < checkboxes.length; i++) {
    selected[checkboxes[i].id.split('-')[0]] = checkboxes[i].checked;
  }
  message = document.getElementById('message').value;
  data = {
    'selected': JSON.stringify(selected),
    'message': message,
  }
  $.post('/telegram/send-notify', data, function() {
    swal("Сообщение отправлено", "", "success");
    document.getElementsByClassName('btn')[0].disabled = false;
  })
}
