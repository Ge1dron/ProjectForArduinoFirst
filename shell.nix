{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    (pkgs.python3.withPackages (ps: [
      ps.pyserial
      ps.numpy
      ps.matplotlib
      ps.tkinter # Необходим для бэкенда TkAgg в matplotlib
    ]))
  ];

  shellHook = ''
    echo "========================================================="
    echo " Среда Nix для обработки FFT с Arduino успешно запущена! "
    echo " Запустите скрипт командой: python fft_receiver.py     "
    echo "========================================================="
  '';
}
